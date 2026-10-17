"""Builder scope must be checked before any test resources are acquired."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuilderBoundaryTests(unittest.TestCase):
    def test_actual_managed_image_setup_is_not_a_full_test_suite(self):
        image = load('android-managed-image')
        command = image.setup_command()
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[1]).name, 'gradle-gate.py')
        args = command[2:]
        path = Path(__file__).resolve().parents[1] / 'dispatcher/scripts/test-selection.py'
        spec = importlib.util.spec_from_file_location('shared_mobile_image_policy_contract', path)
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
        policy.selection('gradle', args)
        for combined in [args + ['check'], args + [':app:' + image.DEVICE + 'DebugAndroidTest']]:
            with self.subTest(args=combined), self.assertRaises(ValueError):
                policy.selection('gradle', combined)
        with self.assertRaises(ValueError):
            policy.selection('android', ['ui'])

    def test_shared_policy_accepts_real_focused_and_nested_mobile_argument_shapes(self):
        path = Path(__file__).resolve().parents[1] / 'dispatcher/scripts/test-selection.py'
        spec = importlib.util.spec_from_file_location('shared_mobile_policy_contract', path)
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
        method = "de.pyryco.mobile.ExampleTest#a comma, apostrophe's method"
        permitted = [('android', ['ui', '--tests', 'de.pyryco.mobile.ExampleTest']),
                     ('android', ['ui', '--tests', 'de.pyryco.mobile.recording.RecordedMobileSuiteTest#oneScenario']),
                     ('android', ['scripted', 'ping']),
                     ('jvm', ['--classes', 'de.pyryco.mobile.ExampleTest']),
                     ('jvm', ['--tests-json', json.dumps([method])]),
                     ('gradle', [':app:testDebugUnitTest', '--tests', method.replace('#', '.', 1)]),
                     ('gradle', [':app:pixel2Api33AtdDebugAndroidTest', '-Pandroid.testInstrumentationRunnerArguments.class=de.pyryco.mobile.ExampleTest#works']),
                     ('gradle', [':app:assembleDebug', ':app:assembleDebugAndroidTest', '--console=plain']),
                     ('gradle', ['spotlessApply']), ('gradle', ['compileDebugAndroidTestKotlin'])]
        denied = [('android', ['ui']), ('android', ['scripted-all']),
                  ('android', ['ui', '--tests', 'de.pyryco.mobile.*']),
                  ('android', ['ui', '--tests', 'de.pyryco.mobile.ExampleTest,de.pyryco.mobile.OtherTest']),
                  ('android', ['ui', '--tests', 'de.pyryco.mobile.recording.RecordedMobileSuiteTest']),
                  ('jvm', []), ('jvm', ['--classes', '']), ('jvm', ['--classes', 'de.pyryco.mobile.*']),
                  ('jvm', ['--tests-json', '[]']),
                  ('gradle', ['check']), ('gradle', ['testDebugUnitTest'])]
        for kind, args in permitted:
            with self.subTest(kind=kind, args=args):
                policy.selection(kind, args)
        for kind, args in denied:
            with self.subTest(kind=kind, args=args), self.assertRaises(ValueError):
                policy.selection(kind, args)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            context = root / '.git/pyry-test-context'
            context.mkdir(parents=True)
            record = {'version': 1, 'root': str(root), 'runId': 'run', 'project': 'mobile', 'socket': '/private/tmp/fake-scope.sock'}
            (context / 'context.json').write_text(json.dumps(record))
            # The temporary binding represents the actual caller's worktree.
            # Authority comes from the frozen RPC reply, never role-like environment.
            with patch.object(policy.Path, 'cwd', return_value=root):
                for role in ['builder', 'verifier']:
                    with patch.object(policy, 'socket_context', return_value={**record, 'role': role, 'origin': 'agent'}):
                        for kind, args in [('android', ['ui']), ('jvm', []), ('gradle', ['check'])]:
                            with self.subTest(role=role, kind=kind):
                                spoof = {'PYRY_TASK_ROLE': 'verifier', 'PYRY_TASK_ORIGIN': 'dispatcher-gate'}
                                if role == 'builder':
                                    with self.assertRaises(ValueError):
                                        policy.check(root, kind, args, spoof)
                                else:
                                    policy.check(root, kind, args, spoof)

    def test_android_full_environment_remains_subordinate_to_explicit_selection(self):
        gate = load('android-test-gate')
        selected = 'de.pyryco.mobile.ExampleTest#works'
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate, 'ROOT', Path(directory)), \
                    patch.object(sys, 'argv', ['gate', 'ui', '--tests', selected]), \
                    patch.dict(os.environ, {'UI_GATE_FULL': '1', 'UI_DEVICE_ALL': '1',
                                            'PYRY_GATE_SELECTED_TESTS': 'stale'}, clear=True), \
                    patch.object(gate, 'check_selection'), patch.object(gate, 'device_hold', return_value=contextlib.nullcontext()), \
                    patch.object(gate, 'build_apks', return_value=0), patch.object(gate, 'run_on_device', return_value=0) as execute:
                self.assertEqual(gate.main(), 0)
                command, env = execute.call_args.args[:2]
                self.assertIn('-Pandroid.testInstrumentationRunnerArguments.class=' + selected, command)
                self.assertEqual(env['PYRY_GATE_SELECTED_TESTS'], selected)
            with patch.object(sys, 'argv', ['gate', 'ui', '--tests', selected, '--full']), \
                    patch.object(gate, 'check_selection'), patch.object(gate.tempfile, 'mkdtemp') as artifacts, \
                    patch.object(gate, 'device_hold') as hold:
                with self.assertRaises(SystemExit):
                    gate.main()
                artifacts.assert_not_called()
                hold.assert_not_called()

    def test_bridge_uses_own_pinned_policy_and_preserves_root_args_and_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copy2(Path(__file__).with_name('test-selection.py'), scripts / 'test-selection.py')
            policy = root / 'dispatcher/scripts/test-selection.py'
            policy.parent.mkdir(parents=True)
            receipt = root / 'receipt.json'
            policy.write_text('import json\nfrom pathlib import Path\ndef check(root, kind, args, env):\n'
                              '    Path(' + repr(str(receipt)) + ').write_text(json.dumps([str(root),kind,args,env]))\n')
            spec = importlib.util.spec_from_file_location('selection_bridge', scripts / 'test-selection.py')
            bridge = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bridge)
            args = ['--tests-json', '["de.pyryco.mobile.ExampleTest#a comma, apostrophe\'s method"]']
            bridge.check_selection(root, 'jvm', args, {'PYRY_TASK_SOCKET': 'retained'})
            self.assertEqual(json.loads(receipt.read_text()), [str(root), 'jvm', args, {'PYRY_TASK_SOCKET': 'retained'}])
            policy.write_text('def check(*args):\n    raise ValueError("unselected builder suite")\n')
            with self.assertRaisesRegex(SystemExit, 'unselected builder suite'):
                bridge.check_selection(root, 'android', ['ui'])

    def test_android_refuses_before_branch_skip_artifacts_or_device_hold(self):
        gate = load('android-test-gate')
        with patch.object(sys, 'argv', ['android-test-gate.py', 'ui']), \
                patch.object(gate, 'check_selection', side_effect=SystemExit('focused selection required')) as check, \
                patch.object(gate, 'changed_paths') as paths, patch.object(gate, 'device_hold') as hold, \
                patch.object(gate.tempfile, 'mkdtemp') as artifacts:
            with self.assertRaisesRegex(SystemExit, 'focused selection'):
                gate.main()
            check.assert_called_once_with(gate.ROOT, 'android', ['ui'])
            paths.assert_not_called()
            artifacts.assert_not_called()
            hold.assert_not_called()

    def test_jvm_refuses_before_report_directory_or_gradle_launch(self):
        gate = load('jvm-test-gate')
        with patch.object(sys, 'argv', ['jvm-test-gate.py']), \
                patch.object(gate, 'check_selection', side_effect=SystemExit('focused selection required')) as check, \
                patch.object(gate.subprocess, 'run') as launch, patch.object(gate.tempfile, 'mkdtemp') as artifacts:
            with self.assertRaisesRegex(SystemExit, 'focused selection'):
                gate.main()
            check.assert_called_once_with(gate.ROOT, 'jvm', [])
            launch.assert_not_called()
            artifacts.assert_not_called()

    def test_gradle_refuses_before_installation_probe_or_exec(self):
        gate = load('gradle-gate')
        with patch.object(sys, 'argv', ['gradle-gate.py', 'check']), \
                patch.object(gate, 'check_selection', side_effect=SystemExit('focused selection required')) as check, \
                patch.object(gate, 'launch') as launch, patch.object(gate.os, 'execve') as execute:
            with self.assertRaisesRegex(SystemExit, 'focused selection'):
                gate.main()
            check.assert_called_once_with(gate.ROOT, 'gradle', ['check'])
            launch.assert_not_called()
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
