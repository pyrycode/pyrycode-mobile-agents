import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('focused_gate',Path(__file__).with_name('android-test-gate.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
CASE='de.pyryco.mobile.ui.SavedThreadFirstDrawDeviceTest#firstOpen'


class FocusedGateTests(unittest.TestCase):
    def test_explicit_ui_selection_uses_shared_admission_even_on_script_only_branch(self):
        with tempfile.TemporaryDirectory() as d:
            held=[];observed=[]
            @contextlib.contextmanager
            def hold(*_):
                held.append(True)
                try:yield
                finally:held.pop()
            def build(env,mode):
                observed.append(('build',bool(held),env.copy()));return 0
            def run(command,env,*_):
                observed.append(('run',bool(held),env.copy(),command));return 0
            with patch.object(gate,'ROOT',Path(d)),patch.object(sys,'argv',['gate','ui','--tests',CASE]), \
                 patch.dict(os.environ,{},clear=True),patch.object(gate,'changed_paths',return_value=['scripts/example.py']), \
                 patch.object(gate,'device_hold',hold),patch.object(gate,'build_apks',side_effect=build), \
                 patch.object(gate,'run_on_device',side_effect=run),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(gate.main(),0)
            self.assertEqual([x[0] for x in observed],['build','run'])
            self.assertTrue(all(x[1] for x in observed),'compilation and measurements must share admission')
            self.assertIn('-Pandroid.testInstrumentationRunnerArguments.class='+CASE,observed[-1][3])
            self.assertEqual(observed[0][2]['ORG_GRADLE_PROJECT_kotlin.compiler.execution.strategy'],'in-process')

    def test_selector_rejects_shell_input_foreign_packages_and_empty_names(self):
        for value in ['','Other#method','de.pyryco.mobile.ui.Test#ok;touch /tmp/x','de.pyryco.mobile.ui.Test#','de.pyryco.mobile.ui.Test,']:
            with self.subTest(value=value):self.assertIsNone(gate.parse_ui_tests(value))
        self.assertEqual(gate.parse_ui_tests(CASE+','+CASE),[CASE])

    def test_selected_method_must_actually_execute_without_skipping(self):
        for report in ['<testsuite><testcase classname="de.pyryco.mobile.ui.SavedThreadFirstDrawDeviceTest" name="other"/></testsuite>',
                       '<testsuite><testcase classname="de.pyryco.mobile.ui.SavedThreadFirstDrawDeviceTest" name="firstOpen"><skipped/></testcase></testsuite>']:
            with self.assertRaises(ValueError):gate.require_selected_tests(report,[CASE])
        gate.require_selected_tests('<testsuite><testcase classname="de.pyryco.mobile.ui.SavedThreadFirstDrawDeviceTest" name="firstOpen"/></testsuite>',[CASE])

    def test_apk_compilation_uses_existing_owned_process_cleanup(self):
        with patch.object(gate,'run_device_command',return_value=subprocess.CompletedProcess([],0)) as owned, \
             patch.object(gate.subprocess,'run',side_effect=AssertionError('unowned compilation')):
            self.assertEqual(gate.build_apks({},'ui'),0)
        self.assertEqual(owned.call_count,1)


if __name__=='__main__':unittest.main()
