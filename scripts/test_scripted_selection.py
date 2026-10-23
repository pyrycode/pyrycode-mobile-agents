"""Named scripted reruns preserve the original scenario and counted evidence."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('selected_scripted_gate', Path(__file__).with_name('android-test-gate.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
CLASS = gate.E2E_PACKAGE + '.DeterministicInteractiveStreamE2ETest'
METHOD = 'interactiveTurn_seededChannel_showsThinkingSpinnerDuringTurn'


class ScriptedSelectionTests(unittest.TestCase):
    def test_selection_maps_exact_test_to_its_original_scenario(self):
        self.assertEqual(gate.scripted_selection(CLASS + '#' + METHOD), [('spinner', CLASS + '#' + METHOD)])
        for name in ['unknown', CLASS + '#unknown', CLASS + '#' + METHOD + ';echo nope', CLASS + '#' + METHOD + ',']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                gate.scripted_selection(name)

    def test_companion_methods_select_their_original_scenarios(self):
        methods = [
            ('session-error', 'interactiveTurn_sessionError_recoversDroppedAndRetainedBacklog'),
            ('background-agent', 'interactiveTurn_seededChannel_earlierSessionAgent_survivesRestartAndSettlementReconnect'),
            ('background-agent', 'interactiveTurn_seededChannel_backgroundAgentMovesAndSettles'),
            ('ping', 'interactiveTurn_seededChannel_durableGapCatchUp'),
            ('ping', 'interactiveTurn_seededChannel_streamsScriptedPingReplyIntoThread'),
            ('stream', 'interactiveTurn_seededChannel_queuedPromptDoesNotSplitHeldReply'),
        ]
        self.assertEqual(gate.scripted_selection(','.join(CLASS + '#' + method for _, method in methods)),
                         [(scenario, CLASS + '#' + method) for scenario, method in methods])

    def test_multiple_selected_methods_run_the_original_scenario_once(self):
        methods = ['interactiveTurn_seededChannel_durableGapCatchUp',
                   'interactiveTurn_seededChannel_streamsScriptedPingReplyIntoThread']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / 'app/build/outputs/androidTest-results/managedDevice/debug/pixel2Api33Atd'
            reports.mkdir(parents=True)
            evidence = root / 'evidence'
            evidence.mkdir()
            scenarios = []
            def run(command, **kwargs):
                scenarios.append(kwargs['env']['SCENARIO'])
                cases = ''.join(f'<testcase classname="{CLASS}" name="{method}"/>' for method in methods)
                (reports / 'TEST-ping.xml').write_text(f'<testsuite tests="2">{cases}</testsuite>')
                return subprocess.CompletedProcess(command, 0)
            with patch.object(gate, 'ROOT', root), patch.object(gate, 'managed_avd', return_value=None), \
                 patch.object(gate, 'run_device_command', side_effect=run), patch.object(gate.signal, 'signal'), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = gate.run_scripted_all({}, evidence, 'pixel2Api33Atd',
                                               [('ping', CLASS + '#' + method) for method in methods])
            self.assertEqual(scenarios, ['ping'])
            self.assertEqual(status, 0)

    def test_companion_mapping_uses_guarded_data_and_rejects_executable_declarations(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(gate, 'ROOT', Path(directory)):
            scripts = Path(directory) / 'scripts'
            scripts.mkdir()
            shell = scripts / 'e2e-emulator.sh'
            shell.write_text('''if [ -n "${DETERMINISTIC}" ] && [ "${SCENARIO:-}" = "background-agent" ] && [ -z "${E2E_BACKGROUND_AGENT_CASE:-}" ]; then
  exec python3 "${REPO_ROOT}/scripts/e2e-background-agent-scenarios.py"
fi
''')
            runner = scripts / 'e2e-background-agent-scenarios.py'
            runner.write_text("METHODS = {'restart': 'companionMethod'}\nraise RuntimeError('must never execute')\n")
            self.assertEqual(gate.scripted_selection(CLASS + '#companionMethod'),
                             [('background-agent', CLASS + '#companionMethod')])
            for declaration in ["METHODS = load_methods()", "METHODS = {'restart': 'bad;method'}",
                                "METHODS = {}", "METHODS = {'restart': 'companionMethod'}\nMETHODS = {}"]:
                runner.write_text(declaration)
                with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                    gate.scripted_selection(CLASS + '#companionMethod')

    def test_missing_or_changed_mapping_refuses_before_any_device_work(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(gate, 'ROOT', Path(directory)):
            with self.assertRaises(ValueError):
                gate.scripted_selection(CLASS + '#' + METHOD)

    def test_selected_run_executes_only_original_scenario_and_requires_exact_result(self):
        for actual_method in [METHOD, 'anotherMethod']:
            with self.subTest(method=actual_method), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                reports = root / 'app/build/outputs/androidTest-results/managedDevice/debug/pixel2Api33Atd'
                reports.mkdir(parents=True)
                run_dir = root / 'evidence'
                run_dir.mkdir()
                scenarios = []
                def run(command, **kwargs):
                    scenarios.append(kwargs['env']['SCENARIO'])
                    (reports / 'TEST-selected.xml').write_text(f'<testsuite tests="1"><testcase classname="{CLASS}" name="{actual_method}"/></testsuite>')
                    return subprocess.CompletedProcess(command, 0)
                with patch.object(gate, 'ROOT', root), patch.object(gate, 'managed_avd', return_value=None), \
                     patch.object(gate, 'run_device_command', side_effect=run), patch.object(gate.signal, 'signal'), \
                     contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    status = gate.run_scripted_all({}, run_dir, 'pixel2Api33Atd', [('spinner', CLASS + '#' + METHOD)])
                self.assertEqual(scenarios, ['spinner'])
                self.assertEqual(status, 0 if actual_method == METHOD else 1)


if __name__ == '__main__':
    unittest.main()
