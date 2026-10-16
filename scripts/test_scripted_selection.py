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
