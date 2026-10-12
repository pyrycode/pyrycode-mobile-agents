"""Real cancellation must join fixture cleanup before releasing the device."""
import os
import fcntl
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

GATE = Path(__file__).with_name('android-test-gate.py')
DRIVER = '''import importlib.util,os,pathlib,sys
spec=importlib.util.spec_from_file_location('gate',sys.argv[1]);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
r=pathlib.Path(sys.argv[2])
with g.device_hold('cancellation-test',0):
 g.run_on_device(['bash',str(r/'fixture.sh')],os.environ.copy(),r,'unused',1,'unused')
'''

class CancellationTest(unittest.TestCase):
    def test_cancellation_waits_for_fixture_cleanup(self):
        for sig in [signal.SIGINT,signal.SIGTERM]:
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                (root/'fixture.sh').write_text('''#!/bin/bash
cleanup() { trap '' INT TERM; kill "$child" 2>/dev/null; wait "$child" 2>/dev/null; echo cleaning > "$CHECK_ROOT/cleaning"; sleep 0.4; echo done > "$CHECK_ROOT/done"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
sleep 60 &
child=$!
echo "$child" > "$CHECK_ROOT/child"
echo ready > "$CHECK_ROOT/ready"
wait "$child"
''')
                env=dict(os.environ,CHECK_ROOT=tmp,ANDROID_USER_HOME=tmp)
                with open(root/'output','w') as output:
                    p=subprocess.Popen([sys.executable,'-c',DRIVER,str(GATE),tmp],env=env,stdout=output,stderr=output,start_new_session=True)
                    try:
                        deadline=time.monotonic()+5
                        while not (root/'ready').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                        self.assertTrue((root/'ready').exists(),(root/'output').read_text())
                        os.kill(p.pid,sig)
                        deadline=time.monotonic()+5
                        while not (root/'cleaning').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                        self.assertTrue((root/'cleaning').exists(),'cleanup did not start')
                        with open(root/'avd/pyrycode-device-gate.lock') as lock:
                            with self.assertRaises(BlockingIOError):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        os.kill(p.pid,sig)  # A second cancellation must not cut cleanup short.
                        p.wait(timeout=8)
                        self.assertTrue((root/'done').exists(),'device owner exited before fixture cleanup finished')
                        with self.assertRaises(ProcessLookupError):os.kill(int((root/'child').read_text()),0)
                    finally:
                        if p.poll() is None:p.kill();p.wait()
                        try:os.killpg(p.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        if (root/'child').exists():
                            try:os.kill(int((root/'child').read_text()),signal.SIGKILL)
                            except ProcessLookupError:pass

if __name__=='__main__':unittest.main()
