"""Regressions for OS-only managed image preparation and snapshot compatibility."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('image', Path(__file__).with_name('android-managed-image.py'))
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


class ManagedImageTest(unittest.TestCase):
    def record(self, directory, extra=()):
        args = ['/sdk/emulator/emulator', '@dev33_google_atd_x86_64_Pixel_2',
                '-no-window', '-no-boot-anim', '-no-audio', '-delay-adb', '-show-kernel',
                '-gpu', 'auto-no-window', '-force-snapshot-load', '-read-only', '-no-snapshot-save',
                '-id', 'old_GradleManagedDevice', *extra]
        path = directory / 'emu-launch-params.txt'
        path.write_text('\n'.join(['/work/mobile', '/sdk/emulator/emulator', str(len(args)), *args]) + '\n')
        return path

    def test_preserves_gradle_hardware_flags_and_existing_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = image.preparation_command(self.record(Path(tmp)), '/sdk/emulator/emulator',
                                                'dev33_google_atd_x86_64_Pixel_2', 5600)
        self.assertEqual(command[0], '/sdk/emulator/emulator')
        self.assertIn('-delay-adb', command)
        self.assertEqual(command[command.index('-gpu') + 1], 'auto-no-window')
        self.assertNotIn('-read-only', command)
        self.assertNotIn('-no-snapshot-save', command)
        self.assertIn('-force-snapshot-load', command)
        self.assertEqual(command[command.index('-port') + 1], '5600')
        self.assertNotEqual(command[command.index('-id') + 1], 'old_GradleManagedDevice')

    def test_refuses_unknown_hardware_arguments_instead_of_dropping_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'unsupported'):
                image.preparation_command(self.record(Path(tmp), ['-cores', '8']), '/sdk/emulator/emulator',
                                          'dev33_google_atd_x86_64_Pixel_2', 5600)

    def test_refuses_wrong_device_or_malformed_launch_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.record(Path(tmp))
            with self.assertRaises(ValueError):
                image.preparation_command(path, '/sdk/emulator/emulator', 'other-device', 5600)
            path.write_text('not a launch record\n')
            with self.assertRaises(ValueError):
                image.preparation_command(path, '/sdk/emulator/emulator', 'dev33_google_atd_x86_64_Pixel_2', 5600)

    def test_wrapper_native_record_still_invokes_the_configured_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.record(Path(tmp))
            lines = path.read_text().splitlines()
            lines[1] = lines[3] = '/sdk/emulator/emulator.hp-native'
            path.write_text('\n'.join(lines) + '\n')
            command = image.preparation_command(path, '/sdk/emulator/emulator',
                                                'dev33_google_atd_x86_64_Pixel_2', 5600)
            self.assertEqual(command[0], '/sdk/emulator/emulator')

    def test_environment_preserves_original_signer_and_does_not_mutate_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'original'
            original.mkdir()
            (original / 'debug.keystore').write_bytes(b'synthetic signer identity')
            parent = {'ANDROID_USER_HOME': str(original), 'HOME': '/home/agent', 'EXISTING': 'retained'}
            child = image.generation_environment(parent, root / 'generation')
            self.assertEqual(parent['ANDROID_USER_HOME'], str(original))
            self.assertEqual(child['HOME'], '/home/agent')
            self.assertEqual(child['EXISTING'], 'retained')
            self.assertEqual((Path(child['ANDROID_USER_HOME']) / 'debug.keystore').resolve(),
                             (original / 'debug.keystore').resolve())

    def test_quiet_qualification_requires_a_continuous_interval(self):
        ticks = [0.0]
        values = iter([95] * 39 + [0] + [95] * 40)
        rows = image.wait_for_quiet(lambda: next(values), lambda: ticks[0],
                                    lambda delay: ticks.__setitem__(0, ticks[0] + delay), 30)
        self.assertEqual(len(rows), 80)
        self.assertGreaterEqual(ticks[0], 20)

    def test_busy_guest_times_out_without_lowering_idle_requirement(self):
        ticks = [0.0]
        with self.assertRaisesRegex(RuntimeError, 'settle'):
            image.wait_for_quiet(lambda: 79, lambda: ticks[0],
                                 lambda delay: ticks.__setitem__(0, ticks[0] + delay), 2)

    def test_ready_record_requires_unchanged_snapshot_memory_and_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            ram = directory / 'ram.bin'
            disk = directory / 'userdata-qemu.img.qcow2'
            ram.write_bytes(b'memory')
            disk.write_bytes(b'disk')
            record = {'identity': 'expected', 'files': image.file_records(directory, [ram, disk])}
            self.assertTrue(image.record_matches(directory, record, 'expected'))
            self.assertFalse(image.record_matches(directory, record, 'other'))
            disk.write_bytes(b'changed disk')
            self.assertFalse(image.record_matches(directory, record, 'expected'))

    def test_new_disk_checkpoint_invalidates_the_prepared_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            ram = directory / 'ram.bin'
            ram.write_bytes(b'memory')
            record = {'identity': 'expected', 'files': image.file_records(directory, [ram]),
                      'disks': {'userdata': {'id': '1', 'date': 10}}}
            self.assertTrue(image.record_matches(directory, record, 'expected', record['disks']))
            self.assertFalse(image.record_matches(directory, record, 'expected',
                                                  {'userdata': {'id': '1', 'date': 20}}))

    def test_ignored_console_save_cannot_publish_an_unchanged_checkpoint(self):
        before = {'ram.bin': {'mtimeNs': 1, 'size': 10}, 'hardware.ini': {'mtimeNs': 1}}
        disks = {'disk': {'snapshot': {'date-sec': 1}}}
        with self.assertRaisesRegex(RuntimeError, 'did not save'):
            image.require_saved_checkpoint(before, before, disks, disks)
        with self.assertRaisesRegex(RuntimeError, 'did not save'):
            image.require_saved_checkpoint(before, {'ram.bin': {'mtimeNs': 2}}, disks, disks)
        changed_disk = {'disk': {'snapshot': {'date-sec': 2}}}
        with self.assertRaisesRegex(RuntimeError, 'did not save'):
            image.require_saved_checkpoint(before, {**before, 'hardware.ini': {'mtimeNs': 2}},
                                           disks, changed_disk)
        image.require_saved_checkpoint(before, {'ram.bin': {'mtimeNs': 2}}, disks,
                                       {'disk': {'snapshot': {'date-sec': 2}}})

    def test_mutable_snapshot_metadata_must_still_exist_and_be_nonempty(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            ram = directory / 'ram.bin'
            metadata = directory / 'snapshot.pb'
            ram.write_bytes(b'memory')
            metadata.write_bytes(b'load metadata')
            record = {'identity': 'expected', 'files': image.file_records(directory, [ram]),
                      'requiredMetadata': ['snapshot.pb']}
            self.assertTrue(image.record_matches(directory, record, 'expected'))
            metadata.write_bytes(b'changed load metadata')
            self.assertTrue(image.record_matches(directory, record, 'expected'))
            metadata.write_bytes(b'')
            self.assertFalse(image.record_matches(directory, record, 'expected'))
            metadata.unlink()
            self.assertFalse(image.record_matches(directory, record, 'expected'))

    def test_same_device_inputs_share_a_generation_across_product_worktrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sdk = base / 'sdk'
            for name in ['emulator/source.properties', 'emulator/emulator',
                         'system-images/android-33/google_atd/x86_64/source.properties']:
                path = sdk / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic installed input')
            roots = [base / 'one', base / 'two']
            for root in roots:
                (root / 'app').mkdir(parents=True)
                (root / 'app/build.gradle.kts').write_text('same device declaration')
            first, _ = image.identity_for(roots[0], base / 'android', sdk)
            second, _ = image.identity_for(roots[1], base / 'android', sdk)
            self.assertEqual(first, second)
            (roots[1] / 'gradle.properties').write_text('android.testoptions.manageddevices.emulator.gpu=swangle\n')
            changed, _ = image.identity_for(roots[1], base / 'android', sdk)
            self.assertNotEqual(first, changed)

    def test_main_reuses_ready_generation_and_retains_it_when_metadata_is_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'android'
            original.mkdir()
            (original / 'debug.keystore').write_bytes(b'synthetic signer')
            identity = original / 'pyrycode-managed-images/expected'
            generation = image.new_attempt(identity)
            ram, metadata = generation / 'ram.bin', generation / 'snapshot.pb'
            ram.write_bytes(b'memory')
            metadata.write_bytes(b'metadata')
            record = {'identity': 'expected', 'generation': generation.name,
                      'files': image.file_records(generation, [ram]), 'disks': {'disk': 'saved'},
                      'requiredMetadata': ['snapshot.pb']}
            image.atomic(identity / 'ready.json', record)
            report = root / 'report.json'
            with patch.dict(os.environ, {'ANDROID_USER_HOME': str(original), 'ANDROID_HOME': '/sdk',
                                         'PYRY_MOBILE_REPO': str(root)}), \
                    patch.object(image.sys, 'argv', ['image', '--report', str(report)]), \
                    patch.object(image, 'ensure_system_image'), \
                    patch.object(image, 'identity_for', return_value=('expected', {})), \
                    patch.object(image, 'disk_records', return_value={'disk': 'saved'}), \
                    patch.object(image, 'new_attempt', side_effect=RuntimeError('fresh attempt reached')) as attempt:
                self.assertEqual(image.main(), 0)
                self.assertTrue(json.loads(report.read_text())['reused'])
                attempt.assert_not_called()
                metadata.unlink()
                with self.assertRaisesRegex(RuntimeError, 'fresh attempt reached'):
                    image.main()
                attempt.assert_called_once_with(identity)
            self.assertTrue(ram.is_file())
            self.assertTrue((identity / 'ready.json').is_file())

    def test_failed_attempt_is_retained_while_a_new_attempt_can_prepare(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = Path(tmp) / 'identity'
            first = image.new_attempt(identity)
            (first / 'failure.log').write_text('bounded setup failure')
            second = image.new_attempt(identity)
            self.assertNotEqual(first, second)
            self.assertEqual((first / 'failure.log').read_text(), 'bounded setup failure')
            self.assertTrue(second.is_dir())

    def test_missing_system_image_uses_supported_setup_before_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / 'sdk'
            metadata = sdk / 'system-images/android-33/google_atd/x86_64/source.properties'
            def installed(*args, **kwargs):
                metadata.parent.mkdir(parents=True)
                metadata.write_text('installed image metadata')
                return Mock(returncode=0)
            with patch.object(image.subprocess, 'run', side_effect=installed) as run:
                image.ensure_system_image(root, sdk, {}, root / 'setup.log')
            self.assertIn(':app:pixel2Api33AtdSetup', run.call_args.args[0])
            with patch.object(image.subprocess, 'run') as run:
                image.ensure_system_image(root, sdk, {}, root / 'setup.log')
            run.assert_not_called()


class GatePreparationTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('android-test-gate.py'))
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        sdk = self.directory / 'sdk'
        (sdk / 'emulator').mkdir(parents=True)
        (sdk / 'emulator/emulator').write_text('synthetic launcher')
        self.env = {'ANDROID_HOME': str(sdk), 'ANDROID_USER_HOME': '/original/shared/android'}
        self.enterContext(patch.object(self.gate.sys, 'platform', 'linux'))

    def test_preparation_uses_existing_custody_and_only_changes_the_child_environment(self):
        self.gate._DEVICE_HOLD_FD = 41
        def owned(command, **kwargs):
            self.assertEqual(self.gate._DEVICE_HOLD_FD, 41)
            self.assertEqual(kwargs['env']['ANDROID_USER_HOME'], '/original/shared/android')
            report = Path(command[command.index('--report') + 1])
            report.write_text(json.dumps({'androidUserHome': '/prepared/android', 'avdHome': '/prepared/android/avd'}))
            return Mock(returncode=0)
        with patch.object(self.gate, 'run_device_command', side_effect=owned) as run:
            child = self.gate.managed_ui_environment(self.env, self.directory, image.DEVICE)
        run.assert_called_once()
        self.assertIn('android-managed-image.py', run.call_args.args[0][1])
        self.assertEqual(child['ANDROID_USER_HOME'], '/prepared/android')
        self.assertEqual(self.env['ANDROID_USER_HOME'], '/original/shared/android')

    def test_failed_preparation_has_no_test_environment_or_passing_report(self):
        with patch.object(self.gate, 'run_device_command', return_value=Mock(returncode=1)):
            with self.assertRaisesRegex(ValueError, 'no device tests started'):
                self.gate.managed_ui_environment(self.env, self.directory, image.DEVICE)
        self.assertFalse((self.directory / 'managed-image.json').exists())

    def test_connected_device_does_not_prepare_a_different_image(self):
        with patch.object(self.gate, 'run_device_command') as run:
            self.assertIs(self.gate.managed_ui_environment(self.env, self.directory, 'connected'), self.env)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
