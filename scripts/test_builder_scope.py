"""Builder scope must be checked before any test resources are acquired."""
import importlib.util
import json
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
                  ('jvm', []), ('jvm', ['--classes', 'de.pyryco.mobile.*']),
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
            for role, origin in [('verifier', 'agent'), ('builder', 'dispatcher-gate')]:
                with patch.object(policy, 'socket_context', return_value={**record, 'role': role, 'origin': origin}):
                    policy.check(root, 'android', ['ui'])
                    policy.check(root, 'jvm', [])
                    policy.check(root, 'gradle', ['check'])

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
