"""Credential-free regressions for the shared verifier cleanup failure."""
import contextlib
import fcntl
import importlib.util
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('android-test-gate.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class CleanupCustodyTest(unittest.TestCase):
    def test_zombie_only_group_is_drained_without_signalling(self):
        rows = subprocess.CompletedProcess([], 0, '42 42 S\n42 43 Z\n77 78 S\n', '')
        with patch.object(gate.subprocess, 'run', return_value=rows), patch.object(os, 'killpg') as kill:
            gate.finish_device_group(SimpleNamespace(pid=42))
        kill.assert_not_called()

    def test_unknown_process_state_never_signals(self):
        with patch.object(gate, 'owned_group_members', side_effect=subprocess.TimeoutExpired('ps', 2)), \
                patch.object(os, 'killpg') as kill:
            with self.assertRaises(gate.CleanupUnconfirmed):
                gate.finish_device_group(SimpleNamespace(pid=42))
        kill.assert_not_called()

    def test_denied_signal_is_not_replayed_and_device_stays_quarantined(self):
        owners = []
        popen = subprocess.Popen
        def start(command, *args, **kwargs):
            child = popen(command, *args, **kwargs)
            if any('android-device-owner.py' in str(arg) for arg in command):
                owners.append(child)
            return child
        with tempfile.TemporaryDirectory() as tmp:
            parent = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])"
            try:
                with patch.dict(os.environ, ANDROID_USER_HOME=tmp), patch.object(subprocess, 'Popen', side_effect=start), \
                        patch.object(os, 'killpg', side_effect=PermissionError('denied')) as kill:
                    with self.assertRaises(gate.CleanupUnconfirmed), gate.device_hold('denial', 0):
                        gate.run_device_command([sys.executable, '-c', parent])
                    self.assertEqual(kill.call_count, 1)
                    with open(gate.device_hold_path()) as lock:
                        with self.assertRaises(BlockingIOError):
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Test-owner recovery only, outside the simulated denial.
                os.killpg(owners[0].pid, signal.SIGKILL)
                owners[0].wait(timeout=3)
                with patch.dict(os.environ, ANDROID_USER_HOME=tmp), self.assertRaises(gate.DeviceBusy):
                    with gate.device_hold('reuse', 0):
                        self.fail('quarantine disappeared with owner exit')
            finally:
                for owner in owners:
                    if owner.poll() is None:
                        os.killpg(owner.pid, signal.SIGKILL)
                        owner.wait(timeout=3)

    def test_parent_loss_preserves_inherited_device_lock(self):
        driver = '''import importlib.util,os,pathlib,sys
spec=importlib.util.spec_from_file_location('gate',sys.argv[1]);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
with g.device_hold('parent-loss',0):
 g.run_device_command([sys.executable,'-c',"import os,pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(os.getpgrp())); time.sleep(.6)",sys.argv[2]])
'''
        with tempfile.TemporaryDirectory() as tmp:
            group_file = Path(tmp) / 'group'
            parent = subprocess.Popen([sys.executable, '-c', driver, str(Path(gate.__file__)), str(group_file)],
                                      env=dict(os.environ, ANDROID_USER_HOME=tmp),
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            group = None
            try:
                deadline = time.monotonic() + 5
                while not group_file.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(group_file.exists())
                group = int(group_file.read_text())
                parent.kill()
                parent.wait(timeout=3)
                time.sleep(.8)  # Child exit and broken report pipe must not release custody.
                with open(Path(tmp) / 'avd/pyrycode-device-gate.lock') as lock:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait(timeout=3)
                if group is not None:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(group, signal.SIGKILL)

    def test_completed_command_does_not_use_permission_sensitive_signal_zero_probe(self):
        original = os.killpg
        def denied_probe(group, sig):
            if sig == 0:
                raise PermissionError('recorded signal-zero denial')
            return original(group, sig)
        with patch.object(os, 'killpg', side_effect=denied_probe):
            result = gate.run_device_command([sys.executable, '-c', 'raise SystemExit(7)'])
        self.assertEqual(result.returncode, 7)

    def test_surviving_descriptor_closing_child_is_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = Path(tmp) / 'child'
            script = "import os,time,signal; signal.signal(signal.SIGTERM, signal.SIG_IGN); os.closerange(3,256); time.sleep(60)"
            parent = "import subprocess,sys,pathlib,time; p=subprocess.Popen([sys.executable,'-c',sys.argv[2]]); pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(.2)"
            try:
                with patch.object(gate, 'DEVICE_TERM_TIMEOUT', .3):
                    result = gate.run_device_command([sys.executable, '-c', parent, str(pidfile), script])
                self.assertEqual(result.returncode, 0)
                rows = subprocess.check_output(['/bin/ps', '-axo', 'pid=,stat='], text=True)
                self.assertFalse(any(int(pid) == int(pidfile.read_text()) and not state.startswith('Z')
                                     for pid, state in (line.split() for line in rows.splitlines())))
            finally:
                if pidfile.exists():
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(int(pidfile.read_text()), signal.SIGKILL)

    def test_cleanup_error_preserves_single_run_reports_and_blocks_device_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'evidence'
            output.mkdir()
            reports = root / 'app/build/outputs/androidTest-results/connected/debug'
            reports.mkdir(parents=True)
            def failed_cleanup(*args, **kwargs):
                (reports / 'TEST-fresh.xml').write_text('<testsuite tests="1"><testcase classname="test" name="done"/></testsuite>')
                (reports / 'logcat-test.txt').write_text('private fixture log')
                raise gate.CleanupUnconfirmed(12345, 'permission-denied')
            with patch.dict(os.environ, ANDROID_USER_HOME=tmp), patch.object(gate, 'ROOT', root), \
                    patch.object(gate, 'run_device_command', side_effect=failed_cleanup), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(gate.CleanupUnconfirmed), gate.device_hold('test', 0):
                    gate.run_on_device([], {}, output, 'connected', 1, 'test')
                self.assertTrue(list(output.glob('*TEST-fresh.xml')))
                self.assertTrue(list(output.glob('*logcat-test.txt')))
                with self.assertRaises(gate.DeviceBusy):
                    with gate.device_hold('next', 0):
                        self.fail('uncertain cleanup released device')

    def test_scripted_cleanup_error_preserves_reports_without_running_next_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'evidence'
            output.mkdir()
            reports = root / 'app/build/outputs/androidTest-results/managedDevice/debug/unused'
            reports.mkdir(parents=True)
            def failed_cleanup(*args, **kwargs):
                (reports / 'TEST-fresh.xml').write_text('<testsuite tests="1"><testcase classname="test" name="done"/></testsuite>')
                raise gate.CleanupUnconfirmed(12345, 'permission-denied')
            with patch.object(gate, 'ROOT', root), patch.object(gate, 'run_device_command', side_effect=failed_cleanup) as run, \
                    patch.object(gate.signal, 'signal'), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(gate.CleanupUnconfirmed):
                    gate.run_scripted_all({}, output, 'unused')
                self.assertEqual(run.call_count, 1)
                self.assertTrue(list(output.glob('*TEST-fresh.xml')))


if __name__ == '__main__':
    unittest.main()
