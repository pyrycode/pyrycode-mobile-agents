#!/usr/bin/env python3
"""Run the pinned Gradle build in its admitted JVM, without a detached worker."""
import os
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(os.environ.get('PYRY_MOBILE_REPO', Path(__file__).resolve().parents[2] / 'pyrycode-mobile')).resolve()
VERSION = '9.4.1'
JAVA = '21'
MODULE_OPTIONS = [
    '--add-opens=java.base/java.lang=ALL-UNNAMED',
    '--add-opens=java.base/java.lang.invoke=ALL-UNNAMED',
    '--add-opens=java.base/java.util=ALL-UNNAMED',
    '--add-opens=java.prefs/java.util.prefs=ALL-UNNAMED',
    '--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED',
    '--add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED',
    '--add-opens=java.base/java.nio.charset=ALL-UNNAMED',
    '--add-opens=java.base/java.net=ALL-UNNAMED',
    '--add-opens=java.base/java.util.concurrent=ALL-UNNAMED',
    '--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED',
    '--add-opens=java.xml/javax.xml.namespace=ALL-UNNAMED',
    '--add-opens=java.base/java.time=ALL-UNNAMED',
]


def property_value(path, name):
    match = re.search(r'^' + re.escape(name) + r'\s*=\s*(.+)$', path.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError(f'{name} is missing from {path.name}')
    return match[1].strip()


def installation(root, env):
    wrapper = root / 'gradle/wrapper/gradle-wrapper.properties'
    distribution = property_value(wrapper, 'distributionUrl')
    if not distribution.endswith(f'/gradle-{VERSION}-bin.zip'):
        raise ValueError('managed launcher requires the reviewed Gradle 9.4.1 distribution')
    if property_value(root / 'gradle/gradle-daemon-jvm.properties', 'toolchainVersion') != JAVA:
        raise ValueError('managed launcher requires the reviewed JDK 21 policy')
    jdk = Path(env['JAVA_HOME']).resolve()
    if not property_value(jdk / 'release', 'JAVA_VERSION').strip('"').startswith(JAVA + '.'):
        raise ValueError('JAVA_HOME must select JDK 21 to match the project daemon policy')
    cache = Path(env.get('GRADLE_USER_HOME', str(Path.home() / '.gradle')))
    homes = sorted((cache / 'wrapper/dists' / f'gradle-{VERSION}-bin').glob(f'*/gradle-{VERSION}'))
    if len(homes) != 1:
        raise ValueError('install exactly one pinned Gradle 9.4.1 distribution using ./gradlew --version first')
    home = homes[0]
    cli = home / f'lib/gradle-gradle-cli-main-{VERSION}.jar'
    agent = home / f'lib/agents/gradle-instrumentation-agent-{VERSION}.jar'
    if not cli.is_file() or not agent.is_file() or not (jdk / 'bin/java').is_file():
        raise ValueError('managed Java/Gradle installation is incomplete')
    return jdk, cli, agent


def launch(root, args, env):
    jdk, cli, agent = installation(root, env)
    requested = property_value(root / 'gradle.properties', 'org.gradle.jvmargs')
    caller = []
    clean_args = []
    for token in shlex.split(env.get('JAVA_OPTS', '')) + shlex.split(env.get('GRADLE_OPTS', '')):
        if token.startswith('-Dorg.gradle.jvmargs='):
            requested = token.split('=', 1)[1]
        else:
            caller.append(token)
    for token in args:
        if token.startswith('-Dorg.gradle.jvmargs='):
            requested = token.split('=', 1)[1]
        elif token in ('--daemon', '--foreground', '--stop'):
            raise ValueError('managed checks cannot start or stop reusable Gradle daemons')
        else:
            clean_args.append(token)
    options = shlex.split(requested) + caller + MODULE_OPTIONS
    options = list(dict.fromkeys(options))
    prefix = shlex.split(env.get('JAVA_TOOL_OPTIONS', '')) + shlex.split(env.get('JDK_JAVA_OPTIONS', ''))
    suffix = shlex.split(env.get('_JAVA_OPTIONS', ''))
    ambient = [*prefix, *suffix]
    if any('org.gradle.internal.instrumentation.agent=false' in token for token in [*options, *ambient, *args]):
        raise ValueError('managed checks preserve Gradle instrumentation')
    # CurrentProcess filters this agent before comparing client/build JVM options.
    effective = [*prefix, *options, *suffix]
    required = shlex.join(effective)
    child_env = env.copy()
    child_env['ORG_GRADLE_PROJECT_kotlin.compiler.execution.strategy'] = 'in-process'
    command = [str(jdk / 'bin/java'), *options, '-javaagent:' + str(agent),
               '-Dorg.gradle.appname=gradle', '-jar', str(cli), '--no-daemon',
               '-Dorg.gradle.jvmargs=' + required, '-Pkotlin.compiler.execution.strategy=in-process', *clean_args]
    return command, child_env


def main():
    try:
        command, env = launch(ROOT, sys.argv[1:], os.environ)
    except (KeyError, OSError, ValueError) as error:
        sys.exit(f'Managed Gradle: {error}')
    os.execve(command[0], command, env)


if __name__ == '__main__':
    main()
