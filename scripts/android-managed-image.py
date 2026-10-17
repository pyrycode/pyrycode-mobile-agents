#!/usr/bin/env python3
"""Prepare a compatible OS-only Google ATD generation before managed UI tests."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time
import uuid

DEVICE = 'pixel2Api33Atd'
AVD = 'dev33_google_atd_x86_64_Pixel_2'
POLICY = 1
BOOLEAN_FLAGS = {'-no-window', '-no-boot-anim', '-no-audio', '-delay-adb', '-show-kernel', '-verbose'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, path)


def preparation_command(record, executable, name, port):
    lines = record.read_text().splitlines()
    if len(lines) < 4 or not lines[2].isdigit() or int(lines[2]) != len(lines[3:]):
        raise ValueError('malformed emulator launch record')
    args = lines[3:]
    # A configured renderer wrapper execs a native sibling. That native path
    # is recorded by the emulator; preparation must still invoke the wrapper.
    recorded = Path(args[0])
    if (len(args) < 2 or args[1] != '@' + name or recorded.parent != Path(executable).parent
            or not (recorded.name == 'emulator' or recorded.name.startswith('emulator.'))):
        raise ValueError('emulator launch record belongs to another launcher or device')
    kept, gpu, index = [], False, 2
    while index < len(args):
        token = args[index]
        if token in BOOLEAN_FLAGS:
            kept.append(token)
            index += 1
        elif token == '-gpu' and not gpu and index + 1 < len(args):
            kept.extend(args[index:index + 2])
            gpu, index = True, index + 2
        elif token in {'-id', '-port'} and index + 1 < len(args):
            index += 2
        elif token in {'-read-only', '-no-snapshot-save', '-no-snapshot-load', '-force-snapshot-load'}:
            index += 1
        else:
            raise ValueError('unsupported emulator launch argument: ' + token)
    if not gpu or '-delay-adb' not in kept:
        raise ValueError('managed launch lacks its GPU or delayed-ADB setting')
    return [executable, '@' + name, *kept, '-force-snapshot-load',
            '-port', str(port), '-id', uuid.uuid4().hex + '_GradleManagedDevice']


def generation_environment(parent, generation):
    original = Path(parent.get('ANDROID_USER_HOME', str(Path.home() / '.android')))
    generation.mkdir(parents=True, exist_ok=True)
    signer = original / 'debug.keystore'
    target = generation / 'debug.keystore'
    if not signer.is_file():
        raise RuntimeError('managed Android debug signer is missing from the original Android home')
    if target.is_symlink():
        if target.resolve() != signer.resolve():
            raise RuntimeError('prepared Android home has a different debug signer')
    elif target.exists():
        raise RuntimeError('prepared Android home contains an independent debug signer')
    else:
        target.symlink_to(signer)
    return {**parent, 'ANDROID_USER_HOME': str(generation), 'ANDROID_AVD_HOME': str(generation / 'avd')}


def wait_for_quiet(sample, clock=time.monotonic, sleep=time.sleep, timeout=180):
    deadline, consecutive, rows = clock() + timeout, 0, []
    while clock() < deadline:
        sleep(.25)
        percent = sample()
        rows.append({'at': clock(), 'idlePercent': percent})
        consecutive = consecutive + 1 if percent >= 80 else 0
        if consecutive == 40:
            return rows
    raise RuntimeError('managed operating system did not settle before the preparation deadline')


def file_records(directory, paths):
    return {str(path.relative_to(directory)): {'size': path.stat().st_size, 'mtimeNs': path.stat().st_mtime_ns}
            for path in paths}


def require_saved_checkpoint(before_memory, after_memory, before_disks, after_disks):
    # The console can answer OK while -no-snapshot-save ignores the request.
    before_ram = {name: value for name, value in before_memory.items() if Path(name).name == 'ram.bin'}
    after_ram = {name: value for name, value in after_memory.items() if Path(name).name == 'ram.bin'}
    if not before_ram or before_ram == after_ram or before_disks == after_disks:
        raise RuntimeError('settled operating system did not save a new memory and disk checkpoint')


def record_matches(directory, record, identity, disks=None):
    try:
        return (record['identity'] == identity and bool(record['files'])
                and all((directory / name).is_file() and (directory / name).stat().st_size > 0
                        for name in record.get('requiredMetadata', []))
                and record.get('disks', {}) == (disks or {})
                and record['files'] == file_records(directory, [directory / name for name in record['files']]))
    except (OSError, KeyError, TypeError, ValueError):
        return False


def disk_records(sdk, generation):
    """Read saved disk checkpoints, ignoring refcounts changed by read-only boots."""
    result = {}
    for path in sorted(generation.glob('avd/gradle-managed/*.avd/*.qcow2')):
        done = subprocess.run([str(sdk / 'emulator/qemu-img'), 'info', '--output=json', str(path)],
                              text=True, capture_output=True, timeout=15, check=True)
        value = json.loads(done.stdout)
        snapshots = [entry for entry in value.get('snapshots', []) if entry.get('name') == 'default_boot']
        if len(snapshots) != 1:
            raise RuntimeError('managed disk has no unique saved OS checkpoint: ' + path.name)
        result[str(path.relative_to(generation))] = {'snapshot': snapshots[0],
                                                    'virtualSize': value['virtual-size'],
                                                    'backing': value.get('backing-filename')}
    if not result:
        raise RuntimeError('managed image has no saved disk checkpoints')
    return result


def identity_for(root, original, sdk):
    files = {'preparation': Path(__file__), 'deviceDeclaration': root / 'app/build.gradle.kts',
             'emulatorMetadata': sdk / 'emulator/source.properties', 'launcher': sdk / 'emulator/emulator',
             'systemImageMetadata': sdk / 'system-images/android-33/google_atd/x86_64/source.properties'}
    optional = {'gradleProperties': root / 'gradle.properties',
                'dependencyVersions': root / 'gradle/libs.versions.toml',
                'gradleDistribution': root / 'gradle/wrapper/gradle-wrapper.properties',
                'jvmPolicy': root / 'gradle/gradle-daemon-jvm.properties',
                'operatorGradleProperties': Path(os.environ.get('GRADLE_USER_HOME', str(Path.home() / '.gradle'))) / 'gradle.properties'}
    config = original / 'avd/gradle-managed' / (AVD + '.avd/config.ini')
    if config.is_file():
        files['originalDeviceConfiguration'] = config
    settings = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in os.environ.items()
                if (key.startswith('ORG_GRADLE_PROJECT_android.') and 'manageddevices' in key.lower())
                or key in {'ANDROID_EMULATOR_USE_SYSTEM_LIBS', 'ANDROID_EMULATOR_USE_SYSTEM_ANGLE',
                           'ANDROID_EMU_VK_ICD', 'ANDROID_EMU_VULKAN', 'LIBGL_ALWAYS_SOFTWARE',
                           'MESA_LOADER_DRIVER_OVERRIDE', 'VK_ICD_FILENAMES'}}
    for key in ('GRADLE_OPTS', 'JAVA_OPTS'):
        managed = [token for token in shlex.split(os.environ.get(key, '')) if 'manageddevices' in token.lower()]
        if managed:
            settings[key] = hashlib.sha256(json.dumps(managed).encode()).hexdigest()
    inputs = {'policy': POLICY, 'device': DEVICE, 'settings': settings,
              'inputs': {**{name: digest(path) for name, path in files.items()},
                         **{name: digest(path) if path.is_file() else None for name, path in optional.items()}}}
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(), inputs


def new_attempt(identity):
    attempt = identity / ('attempt-' + uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    return attempt


def setup_command():
    return [sys.executable, str(Path(__file__).with_name('gradle-gate.py')),
            ':app:' + DEVICE + 'Setup', '--rerun', '--console=plain']


def ensure_system_image(root, sdk, env, log):
    if (sdk / 'system-images/android-33/google_atd/x86_64/source.properties').is_file():
        return
    with log.open('w') as output:
        subprocess.run(setup_command(), cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT,
                       timeout=600, check=True)
    if not (sdk / 'system-images/android-33/google_atd/x86_64/source.properties').is_file():
        raise RuntimeError('supported managed setup did not install the configured system image')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    root = Path(os.environ['PYRY_MOBILE_REPO'])
    original = Path(os.environ.get('ANDROID_USER_HOME', str(Path.home() / '.android')))
    sdk = Path(os.environ['ANDROID_HOME'])
    ensure_system_image(root, sdk, os.environ, args.report.parent / 'managed-image-bootstrap.log')
    identity, inputs = identity_for(root, original, sdk)
    identity_directory = original / 'pyrycode-managed-images' / identity
    ready = identity_directory / 'ready.json'
    record, generation = None, None
    if ready.is_file():
        try:
            record = json.loads(ready.read_text())
            if not re.fullmatch(r'attempt-[a-f0-9]{32}', record['generation']):
                raise ValueError('invalid generation name')
            generation = identity_directory / record['generation']
            if not record_matches(generation, record, identity, disk_records(sdk, generation)):
                record = None
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError):
            record = None
    if record is not None:
        env = generation_environment(os.environ, generation)
        atomic(args.report, {'identity': identity, 'androidUserHome': env['ANDROID_USER_HOME'],
                             'avdHome': env['ANDROID_AVD_HOME'], 'reused': True})
        return 0
    # One bounded attempt per invocation. Failed generations stay available for
    # diagnosis. The outer device quarantine prevents retries with uncertain custody.
    generation = new_attempt(identity_directory)
    env = generation_environment(os.environ, generation)
    atomic(generation / 'inputs.json', inputs)
    spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('android-test-gate.py'))
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    def interrupted(*_):
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    # Already inside the gate's owned process group and shared admission.
    # Invoke the agents launcher directly, avoiding a second host admission lock.
    with (generation / 'setup.log').open('w') as output:
        subprocess.run(setup_command(), cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=600, check=True)
    avds = generation / 'avd/gradle-managed'
    directory = avds / (AVD + '.avd')
    executable = str(sdk / 'emulator/emulator')
    launch_record = directory / 'emu-launch-params.txt'
    # Save the fresh Gradle record before our own launch replaces it.
    (generation / 'gradle-launch.txt').write_bytes(launch_record.read_bytes())
    adb = str(sdk / 'platform-tools/adb')
    def adb_call(serial, *command, timeout=15):
        done = subprocess.run([adb, '-s', serial, *command], capture_output=True, text=True, timeout=timeout)
        if done.returncode:
            raise RuntimeError('owned preparation ADB command failed: ' + ' '.join(command[:2]))
        return done.stdout
    def boot(read_only, label):
        port = gate.free_emulator_port()
        if port is None:
            raise RuntimeError('no free owned emulator port')
        serial = 'emulator-' + str(port)
        command = preparation_command(generation / 'gradle-launch.txt', executable, AVD, port)
        if read_only:
            command.extend(['-read-only', '-no-snapshot-save'])
        log = generation / (label + '.log')
        with log.open('w') as output:
            process = subprocess.Popen(command, cwd=root, env={**env, 'ANDROID_AVD_HOME': str(avds)},
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        if adb_call(serial, 'shell', 'getprop', 'sys.boot_completed').strip() == '1':
                            break
                    except RuntimeError:
                        pass
                    time.sleep(.5)
                else:
                    raise RuntimeError('owned preparation emulator did not restore and boot')
                if "Successfully loaded snapshot 'default_boot'" not in log.read_text():
                    raise RuntimeError('preparation did not restore its compatible snapshot')
                packages = adb_call(serial, 'shell', 'pm', 'list', 'packages', 'de.pyryco.mobile')
                if re.search(r'^package:de\.pyryco\.mobile(?:\.test)?$', packages, re.M):
                    raise RuntimeError('OS preparation contains Mobile or its instrumentation package')
                def ticks():
                    values = list(map(int, adb_call(serial, 'shell', 'head', '-1', '/proc/stat').split()[1:9]))
                    return sum(values), values[3] + values[4]
                previous = [ticks()]
                def idle():
                    after = ticks()
                    total, quiet = after[0] - previous[0][0], after[1] - previous[0][1]
                    previous[0] = after
                    return quiet * 100 / total if total > 0 else 0
                rows = wait_for_quiet(idle, timeout=max(0, deadline - time.monotonic()))
                atomic(generation / (label + '-cpu.json'), rows)
                (generation / (label + '-hardware.ini')).write_bytes((directory / 'hardware-qemu.ini').read_bytes())
                (generation / (label + '-phone.log')).write_text(adb_call(serial, 'logcat', '-d', '-b', 'all', '-v', 'threadtime'))
                if not read_only:
                    result = adb_call(serial, 'emu', 'avd', 'snapshot', 'save', 'default_boot', timeout=60)
                    if 'KO:' in result or 'OK' not in result:
                        raise RuntimeError('OS-only snapshot save was not confirmed')
                    (generation / 'snapshot-save.txt').write_text(result)
            finally:
                gate.stop_emulator(env, serial, process)
    memory_paths = [directory / 'snapshots/default_boot/ram.bin',
                    directory / 'snapshots/default_boot/hardware.ini']
    before_memory, before_disks = file_records(generation, memory_paths), disk_records(sdk, generation)
    boot(False, 'prepare')
    saved = file_records(generation, [directory / 'snapshots/default_boot/ram.bin',
                                      directory / 'snapshots/default_boot/hardware.ini'])
    disks = disk_records(sdk, generation)
    require_saved_checkpoint(before_memory, saved, before_disks, disks)
    boot(True, 'restore')
    if file_records(generation, [generation / name for name in saved]) != saved or disk_records(sdk, generation) != disks:
        raise RuntimeError('read-only validation replaced the prepared snapshot')
    paths = list((directory / 'snapshots/default_boot').glob('*'))
    # The emulator updates snapshot.pb load counters and qcow2 refcounts while
    # loading a read-only instance. The saved RAM and named disk checkpoints
    # establish generation identity, rather than those mutable metadata bytes.
    paths = [path for path in paths if path.is_file() and path.name not in {'compatible.pb', 'snapshot.pb'}]
    paths.extend(path for path in directory.glob('*.img') if path.is_file())
    paths.append(directory / 'config.ini')
    atomic(ready, {'identity': identity, 'generation': generation.name, 'files': file_records(generation, paths),
                   'requiredMetadata': [str((directory / 'snapshots/default_boot/snapshot.pb').relative_to(generation))],
                   'disks': disks, 'snapshotMetadataSha256': digest(directory / 'snapshots/default_boot/snapshot.pb'),
                   'preparedAt': time.time()})
    atomic(args.report, {'identity': identity, 'androidUserHome': env['ANDROID_USER_HOME'],
                         'avdHome': env['ANDROID_AVD_HOME'], 'reused': False})
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit('Managed Android image: ' + str(error))
