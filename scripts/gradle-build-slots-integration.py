#!/usr/bin/env python3
"""Prove real Gradle slot contention, task lifetime and cache-hit reacquisition."""
import argparse
import tempfile
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--product-root', type=Path, required=True)
parser.add_argument('--gradle-user-home', type=Path, required=True)
parser.add_argument('--slot-directory', type=Path, required=True)
parser.add_argument('--evidence-dir', type=Path)
args = parser.parse_args()
try:
    fd = int(os.environ['PYRY_TEST_ADMISSION_FD'])
    os.fstat(fd)
except (KeyError, ValueError, OSError):
    sys.exit('Run through the product scripts/test-admission.py command.')
base = args.evidence_dir or Path(tempfile.mkdtemp(prefix='pyry-gradle-slot-proof-'))
if args.evidence_dir:
    base.mkdir(parents=True, exist_ok=False)
agents = Path(__file__).resolve().parents[1]
slots = args.slot_directory.resolve(strict=True)
if not (args.gradle_user_home / 'pyry-build-slots').samefile(slots):
    sys.exit('The isolated Gradle user home must share the existing machine slot directory.')
root = base / '.pyrycode-worktrees/slot-contention'
root.mkdir(parents=True)
ready = root / 'ready'
release = root / 'release'
(root / 'settings.gradle').write_text("rootProject.name='slot-contention'\n")
(root / 'build.gradle').write_text("def ready = new File('" + str(ready) + "')\ndef release = new File('" + str(release) + "')\ntasks.register('hold') { doLast { ready.text='ready'; while(!release.exists()) { Thread.sleep(100) } } }\n")
env = os.environ.copy()
env['GRADLE_USER_HOME'] = str(args.gradle_user_home.resolve())
env['PYRY_MOBILE_REPO'] = str(args.product_root.resolve())
summary=[]

def wait_for(predicate, seconds=45):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate(): return
        time.sleep(.1)
    raise AssertionError('probe condition timed out')

for name in ['store', 'reuse']:
    for marker in [ready,release]:
        marker.unlink(missing_ok=True)
    handles=[(slots / ('slot-' + str(i) + '.lock')).open('a+') for i in [1,2]]
    for handle in handles: fcntl.lockf(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    log=base/('slot-contention-'+name+'.log')
    command=[sys.executable,str(agents/'scripts/gradle-gate.py'),
             '-p',str(root),'hold','--configuration-cache','--console=plain',
             '--init-script',str(agents/'gradle/pyry-build-slots.gradle')]
    try:
        with log.open('w') as output:
            child=subprocess.Popen(command,env=env,pass_fds=(fd,),stdout=output,stderr=subprocess.STDOUT)
            wait_for(lambda: 'all 2 places are taken' in log.read_text() or child.poll() is not None)
            assert child.poll() is None,log.read_text()
            assert not ready.exists()
            handles[0].close()
            wait_for(lambda: ready.exists() or child.poll() is not None)
            assert ready.exists(),log.read_text()
            contender=(slots/'slot-1.lock').open('a+')
            try:
                try: fcntl.lockf(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError: pass
                else: raise AssertionError('task ran without holding the released machine slot')
            finally: contender.close()
            handles[1].close()
            release.write_text('release')
            assert child.wait(timeout=30)==0,log.read_text()
        for path in slots.glob('slot-*.lock'):
            with path.open('a+') as handle: fcntl.lockf(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        text=log.read_text()
        assert 'Configuration cache entry discarded' not in text,text
        if name=='reuse': assert 'Reusing configuration cache.' in text,text
        summary.append({'name':name,'blockedWithBothSlotsTaken':True,'heldDuringTask':True,
                        'releasedAfterBuild':True,'cacheReused':'Reusing configuration cache.' in text})
    finally:
        release.write_text('release')
        for handle in handles: handle.close()
(base/'slot-contention-results.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'evidence': str(base), 'results': summary}),flush=True)
