#!/usr/bin/env python3
"""Expose the current Gradle JVM result as named JUnit evidence."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(os.environ.get('PYRY_MOBILE_REPO', Path(__file__).resolve().parents[2] / 'pyrycode-mobile')).resolve()
NAME = re.compile(r'de\.pyryco\.mobile(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+#[A-Za-z_][A-Za-z0-9_]*')


def parse_tests(value):
    names = value.split(',')
    if len(value) > 8192 or len(names) > 64 or any(not NAME.fullmatch(name) for name in names):
        raise ValueError('--tests requires exact Mobile package.Class#method names')
    return list(dict.fromkeys(names))


def parse_tests_json(value):
    try:
        names = json.loads(value)
    except ValueError as error:
        raise ValueError('--tests-json requires a JSON array of exact JVM test names') from error
    if (len(value) > 32768 or not isinstance(names, list) or not 1 <= len(names) <= 64 or
            any(not isinstance(name, str) or len(name) > 1024 or
                not re.fullmatch(r'de\.pyryco\.mobile(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+#[^*\x00-\x1f\x7f]+', name)
                for name in names)):
        raise ValueError('--tests-json requires bounded exact Mobile Class#method names without wildcards')
    return list(dict.fromkeys(names))


def run(tests=None):
    artifacts = Path(os.environ.get('PYRY_GATE_EVIDENCE_DIR') or ROOT / 'build/dispatcher-tests')
    artifacts.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = Path(tempfile.mkdtemp(prefix='jvm-', dir=artifacts))
    command = [str(ROOT / 'gradlew'), ':app:testDebugUnitTest']
    if tests is not None:
        command.append('--rerun')
    command += ['--console=plain', '--no-daemon', '-Pkotlin.compiler.execution.strategy=in-process']
    for name in tests or []:
        command += ['--tests', name.replace('#', '.', 1)]
    started = time.time_ns()
    env = os.environ.copy()
    env['GRADLE_OPTS'] = (env.get('GRADLE_OPTS', '') + ' -Dorg.gradle.daemon=false').strip()
    env['ORG_GRADLE_PROJECT_kotlin.compiler.execution.strategy'] = 'in-process'
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(result.stdout, end='', file=sys.stderr)
    verified_cache = (tests is None and result.returncode == 0 and
                      re.search(r'^> Task :app:testDebugUnitTest (?:FROM-CACHE|UP-TO-DATE)$', result.stdout, re.MULTILINE))
    outcome = re.search(r'^> Task :app:testDebugUnitTest(?: (FROM-CACHE|UP-TO-DATE|FAILED))?$', result.stdout, re.MULTILINE)
    metadata = {'command': command, 'exitCode': result.returncode,
                'gradleTaskOutcome': (outcome.group(1) or 'EXECUTED') if outcome else 'UNKNOWN',
                'reusedGradleResult': bool(verified_cache)}
    suites = ET.Element('testsuites')
    cases = {}
    try:
        reports = sorted((ROOT / 'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml'))
        for path in reports:
            if path.stat().st_mtime_ns < started and not verified_cache:
                continue
            raw = path.read_bytes()
            if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
                raise ValueError('unsafe XML declaration')
            suite = ET.fromstring(raw)
            leaves = suite.findall('testcase')
            if suite.tag != 'testsuite' or int(suite.get('tests', '-1')) != len(leaves):
                raise ValueError('incomplete JVM report')
            failures = sum(case.find('failure') is not None for case in leaves)
            errors = sum(case.find('error') is not None for case in leaves)
            if (suite.find('failure') is not None or suite.find('error') is not None or
                    int(suite.get('failures', '0')) > failures or int(suite.get('errors', '0')) > errors):
                raise ValueError('JVM runner failed without complete named evidence')
            for case in leaves:
                if not case.get('classname') or not case.get('name'):
                    raise ValueError('unnamed JVM test')
                name = case.get('classname') + '#' + case.get('name')
                if name in cases:
                    raise ValueError('duplicate JVM test')
                cases[name] = case
            shutil.copy2(path, destination / path.name)
            suites.append(suite)
        executed = [case for case in cases.values() if case.find('skipped') is None]
        if not executed:
            raise ValueError('no fresh executed JVM tests')
        for name in tests or []:
            if name not in cases or cases[name].find('skipped') is not None:
                raise ValueError('a selected JVM method did not execute')
        xml = ET.tostring(suites, encoding='unicode')
        (destination / 'dispatcher.xml').write_text(xml + '\n')
        metadata.update(executedInReport=len(executed), executedThisInvocation=0 if verified_cache else len(executed),
                        skipped=sum(case.find('skipped') is not None for case in cases.values()),
                        failed=sum(case.find('failure') is not None or case.find('error') is not None for case in executed))
        (destination / 'invocation.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print(xml)
        failed = any(case.find('failure') is not None or case.find('error') is not None for case in executed)
        reuse = 'Gradle verified cached result' if verified_cache else 'fresh execution'
        print(f'JVM gate: {len(executed)} executed in report; {reuse}; artifacts: {destination}', file=sys.stderr)
        return result.returncode or int(failed)
    except (OSError, ValueError, ET.ParseError) as error:
        print(f'JVM gate: {error}; artifacts: {destination}', file=sys.stderr)
        return result.returncode or 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--tests', help='comma-separated exact package.Class#method selection')
    selection.add_argument('--tests-json', help='JSON array of exact Class#method names, including Kotlin names with spaces or commas')
    args = parser.parse_args()
    try:
        tests = parse_tests_json(args.tests_json) if args.tests_json is not None else parse_tests(args.tests) if args.tests is not None else None
    except ValueError as error:
        parser.error(str(error))
    return run(tests)


if __name__ == '__main__':
    sys.exit(main())
