"""The owned Gradle client uses the same JVM requirements as its build."""
import importlib.util
import tempfile
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('managed_gradle', Path(__file__).with_name('gradle-gate.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GradleGateTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        (root / 'gradle/wrapper').mkdir(parents=True)
        (root / 'gradle/wrapper/gradle-wrapper.properties').write_text('distributionUrl=https\\://services.gradle.org/distributions/gradle-9.4.1-bin.zip\n')
        (root / 'gradle/gradle-daemon-jvm.properties').write_text('toolchainVersion=21\n')
        (root / 'gradle.properties').write_text('org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\n')
        jdk = root / 'jdk with spaces'
        (jdk / 'bin').mkdir(parents=True)
        (jdk / 'bin/java').write_text('java')
        (jdk / 'release').write_text('JAVA_VERSION="21.0.10"\n')
        home = root / 'cache/wrapper/dists/gradle-9.4.1-bin/installed/gradle-9.4.1'
        (home / 'lib/agents').mkdir(parents=True)
        (home / 'lib/gradle-gradle-cli-main-9.4.1.jar').write_text('cli')
        (home / 'lib/agents/gradle-instrumentation-agent-9.4.1.jar').write_text('agent')
        return root, {'JAVA_HOME': str(jdk), 'GRADLE_USER_HOME': str(root / 'cache')}

    def test_client_and_build_share_project_heap_module_policy_and_instrumentation(self):
        with tempfile.TemporaryDirectory() as directory:
            root, env = self.fixture(directory)
            command, child = gate.launch(root, ['check'], env)
            requested = next(arg for arg in command if arg.startswith('-Dorg.gradle.jvmargs='))
            self.assertIn('-Xmx2048m', requested)
            self.assertNotIn('-Xms64m', command)
            for arg in gate.MODULE_OPTIONS:
                self.assertIn(arg, command)
                self.assertIn(arg, requested)
            self.assertEqual(sum(arg.startswith('-javaagent:') for arg in command), 1)
            self.assertNotIn('-javaagent:', requested)
            self.assertIn('--no-daemon', command)
            self.assertEqual(child['ORG_GRADLE_PROJECT_kotlin.compiler.execution.strategy'], 'in-process')

    def test_caller_options_and_exact_arguments_are_preserved_without_shell_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root, env = self.fixture(directory)
            env.update(JAVA_OPTS='-Dcustom="value with spaces" -XX:+HeapDumpOnOutOfMemoryError', GRADLE_OPTS='-Dorg.gradle.daemon=false')
            command, child = gate.launch(root, ['--tests', "a name, with 'quotes' and $value"], env)
            self.assertIn('-Dcustom=value with spaces', command)
            self.assertIn('-XX:+HeapDumpOnOutOfMemoryError', command)
            self.assertEqual(command[-1], "a name, with 'quotes' and $value")
            self.assertEqual(child['JAVA_OPTS'], env['JAVA_OPTS'])

    def test_ambient_heap_precedence_matches_the_actual_java_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            root, env = self.fixture(directory)
            env.update(JAVA_TOOL_OPTIONS='-Xmx3072m', JDK_JAVA_OPTIONS='-Xmx4096m', _JAVA_OPTIONS='-Xmx1536m')
            command, _ = gate.launch(root, ['help'], env)
            requested = next(arg for arg in command if arg.startswith('-Dorg.gradle.jvmargs='))
            self.assertLess(requested.index('-Xmx3072m'), requested.index('-Xmx4096m'))
            self.assertLess(requested.index('-Xmx4096m'), requested.index('-Xmx2048m'))
            self.assertLess(requested.index('-Xmx2048m'), requested.index('-Xmx1536m'))

    def test_incompatible_or_missing_installation_never_silently_changes_jdk(self):
        with tempfile.TemporaryDirectory() as directory:
            root, env = self.fixture(directory)
            (Path(env['JAVA_HOME']) / 'release').write_text('JAVA_VERSION="17.0.1"\n')
            with self.assertRaisesRegex(ValueError, 'JDK 21'):
                gate.launch(root, ['help'], env)
            (Path(env['JAVA_HOME']) / 'release').write_text('JAVA_VERSION="21.0.10"\n')
            (root / 'gradle/wrapper/gradle-wrapper.properties').write_text('distributionUrl=https://example.invalid/gradle-9.5-bin.zip\n')
            with self.assertRaisesRegex(ValueError, '9.4.1'):
                gate.launch(root, ['help'], env)

    def test_daemon_control_is_rejected_and_explicit_heap_override_is_honoured(self):
        with tempfile.TemporaryDirectory() as directory:
            root, env = self.fixture(directory)
            for option in ['--daemon', '--stop', '--foreground']:
                with self.assertRaises(ValueError):
                    gate.launch(root, [option], env)
            command, _ = gate.launch(root, ['-Dorg.gradle.jvmargs=-Xmx3072m -Dfile.encoding=UTF-8', 'help'], env)
            self.assertIn('-Xmx3072m', command)
            self.assertNotIn('-Xmx2048m', command)


if __name__ == '__main__':
    unittest.main()
