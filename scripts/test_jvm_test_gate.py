"""Fresh named JVM evidence without a device, Gradle install or account."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('jvm_gate', Path(__file__).with_name('jvm-test-gate.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
CASE = 'de.pyryco.mobile.ExampleTest#works'


class JvmGateTests(unittest.TestCase):
    def run_gate(self, xml=None, code=0, tests=None, stale=False, log='', with_build_checks=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / 'app/build/test-results/testDebugUnitTest'
            reports.mkdir(parents=True)
            def execute(command, **kwargs):
                if xml is not None:
                    path = reports / 'TEST-example.xml'
                    path.write_text(xml)
                    if stale:
                        os.utime(path, ns=(1, 1))
                self.command = command
                self.assertEqual(kwargs['stdout'], subprocess.PIPE)
                return subprocess.CompletedProcess(command, code, stdout=log)
            output = io.StringIO()
            with patch.object(gate, 'ROOT', root), patch.object(gate.subprocess, 'run', side_effect=execute), \
                 patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = gate.run(tests, with_build_checks=with_build_checks)
                metadata = list((root / 'build/dispatcher-tests').glob('jvm-*/invocation.json'))
                self.metadata = json.loads(metadata[0].read_text()) if metadata else None
                self.retained_xml = [path.read_text() for path in (root / 'build/dispatcher-tests').glob('jvm-*/TEST-*.xml')]
            return status, output.getvalue()

    def test_only_named_methods_are_rerun_and_reported(self):
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works" time="0.1"/></testsuite>'
        status, output = self.run_gate(xml, tests=[CASE])
        self.assertEqual(status, 0)
        self.assertIn('--rerun', self.command)
        self.assertIn('--no-daemon', self.command)
        self.assertIn('-Pkotlin.compiler.execution.strategy=in-process', self.command)
        self.assertEqual(self.command[-1], 'de.pyryco.mobile.ExampleTest.works')
        self.assertIn('name="works"', output)

    def test_exact_class_selection_requires_executed_members_of_that_class(self):
        xml = '<testsuite tests="2"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/><testcase classname="de.pyryco.mobile.ExampleTest" name="other"><skipped/></testcase></testsuite>'
        status, _ = self.run_gate(xml, tests=['de.pyryco.mobile.ExampleTest'])
        self.assertEqual(status, 0)
        self.assertEqual(self.command[-1], 'de.pyryco.mobile.ExampleTest')
        self.assertEqual(self.metadata['executedThisInvocation'], 1)
        self.assertEqual(self.metadata['skipped'], 1)
        self.assertNotEqual(self.run_gate(xml, tests=['de.pyryco.mobile.OtherTest'])[0], 0)
        self.assertNotEqual(self.run_gate(xml.replace('name="works"/>', 'name="works"><skipped/></testcase>'),
                                         tests=['de.pyryco.mobile.ExampleTest'])[0], 0)

    def test_stale_empty_missing_and_truncated_reports_cannot_pass(self):
        valid = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        for xml, stale in [(None, False), ('<testsuite tests="0"/>', False), ('<testsuite>', False), (valid, True),
                           (valid.replace('tests="1"', 'tests="2"'), False)]:
            with self.subTest(xml=xml, stale=stale):
                self.assertNotEqual(self.run_gate(xml, stale=stale)[0], 0)

    def test_failed_or_skipped_named_method_cannot_be_hidden_by_other_pass(self):
        for child in ['<failure message="broken"/>', '<skipped/>']:
            xml = '<testsuite tests="2"><testcase classname="de.pyryco.mobile.ExampleTest" name="works">' + child + '</testcase><testcase classname="de.pyryco.mobile.ExampleTest" name="other"/></testsuite>'
            self.assertNotEqual(self.run_gate(xml, tests=[CASE])[0], 0)

    def test_nonzero_build_is_preserved_even_with_passing_xml(self):
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        self.assertEqual(self.run_gate(xml, code=17)[0], 17)

    def test_coordinated_build_uses_one_bounded_gradle_graph_and_retains_named_results(self):
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        self.assertEqual(self.run_gate(xml, with_build_checks=True)[0], 0)
        for task in ['check', ':app:assembleDebug', ':app:compileDebugAndroidTestKotlin']:
            self.assertIn(task, self.command)
        for option in ['--continue', '--configuration-cache', '--max-workers=2']:
            self.assertIn(option, self.command)
        self.assertNotIn('-x', self.command)
        self.assertTrue(self.metadata['withBuildChecks'])

    def test_coordinated_non_test_red_cannot_expose_named_failures_for_baseline_acceptance(self):
        xml = '<testsuite tests="1" failures="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"><failure/></testcase></testsuite>'
        jvm = "Execution failed for task ':app:testDebugUnitTest'."
        for log in ['', 'FAILURE: Build completed with 2 failures.\n' + jvm,
                    "FAILURE: Build failed with an exception.\n\n* What went wrong:\nExecution failed for task ':app:lintDebug'.",
                    'FAILURE: Build failed with an exception.\n\n* What went wrong:\n' + jvm + '\n\n* What went wrong:\nOther failure']:
            with self.subTest(log=log):
                status, output = self.run_gate(xml, code=1, log=log, with_build_checks=True)
                self.assertNotEqual(status, 0)
                self.assertEqual(output, '')
                self.assertIn('outside the JVM test task', self.metadata['evidenceError'])
                self.assertTrue(self.metadata['withBuildChecks'])
                self.assertEqual(self.retained_xml, [xml])

    def test_coordinated_only_jvm_failure_keeps_exact_named_comparison_evidence(self):
        xml = '<testsuite tests="1" failures="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"><failure/></testcase></testsuite>'
        log = "FAILURE: Build failed with an exception.\n\n* What went wrong:\nExecution failed for task ':app:testDebugUnitTest'.\n"
        status, output = self.run_gate(xml, code=1, log=log, with_build_checks=True)
        self.assertNotEqual(status, 0)
        self.assertIn('<failure', output)

    def test_coordinated_build_rejects_narrow_selection_before_launch(self):
        with patch.object(gate.subprocess, 'run') as execute, self.assertRaises(ValueError):
            gate.run([CASE], with_build_checks=True)
        execute.assert_not_called()

    def test_coordinated_cached_jvm_report_requires_success_of_the_entire_build(self):
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        log = '> Task :app:testDebugUnitTest FROM-CACHE\n'
        self.assertEqual(self.run_gate(xml, stale=True, log=log, with_build_checks=True)[0], 0)
        self.assertEqual(self.metadata['executedThisInvocation'], 0)
        self.assertNotEqual(self.run_gate(xml, stale=True, log=log, code=1, with_build_checks=True)[0], 0)

    def test_coordinated_discarded_configuration_cache_is_not_a_successful_trial(self):
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        status, output = self.run_gate(xml, log='Configuration cache entry discarded with 1 problem.\n', with_build_checks=True)
        self.assertNotEqual(status, 0)
        self.assertEqual(output, '')
        self.assertEqual(self.retained_xml, [xml])

    def test_suite_error_without_named_failure_stays_red(self):
        xml = '<testsuite tests="1" errors="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        self.assertNotEqual(self.run_gate(xml)[0], 0)

    def test_default_run_keeps_verified_gradle_cache_but_named_comparison_must_execute(self):
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="works"/></testsuite>'
        for status in ['FROM-CACHE', 'UP-TO-DATE']:
            log = '> Task :app:testDebugUnitTest ' + status + '\n'
            with self.subTest(status=status):
                self.assertEqual(self.run_gate(xml, stale=True, log=log)[0], 0)
                self.assertNotIn('--rerun', self.command)
                self.assertTrue(self.metadata['reusedGradleResult'])
                self.assertEqual(self.metadata['executedThisInvocation'], 0)
                self.assertEqual(self.metadata['gradleTaskOutcome'], status)
                self.assertNotEqual(self.run_gate(xml, stale=True, log=log, code=1)[0], 0)
                self.assertNotEqual(self.run_gate(xml, stale=True, log=log, tests=[CASE])[0], 0)

    def test_selector_is_exact_and_never_shell_or_gradle_option(self):
        self.assertEqual(gate.parse_tests(CASE + ',' + CASE), [CASE])
        for value in ['', '--tests', 'Other#method', CASE + ';touch /tmp/x', CASE + ',']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    gate.parse_tests(value)

    def test_json_selection_preserves_real_kotlin_names_as_one_argument(self):
        method = "a queued row rests 8dp over the baseline, Figma's $row `name`"
        name = 'de.pyryco.mobile.ExampleTest#' + method
        self.assertEqual(gate.parse_tests_json(json.dumps([name])), [name])
        xml = '<testsuite tests="1"><testcase classname="de.pyryco.mobile.ExampleTest" name="' + method + '"/></testsuite>'
        self.assertEqual(self.run_gate(xml, tests=[name])[0], 0)
        self.assertEqual(self.command[-1], 'de.pyryco.mobile.ExampleTest.' + method)
        for value in ['[]', '{}', '[1]', json.dumps([name + '*']), json.dumps([name + '\n']), json.dumps(['Other#method'])]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.parse_tests_json(value)


if __name__ == '__main__':
    unittest.main()
