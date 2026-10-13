#!/usr/bin/env python3
"""Keep the device command's process-group identity and lock until cleanup ends.

The gate alone sends group signals. This owner stays unreaped until the gate has
confirmed that the other group members exited, so the group ID cannot be reused.
An abandoned owner retains the inherited device lock for operator recovery.
"""
import os
import signal
import subprocess
import sys


def child_signals():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)


def main():
    report, release = map(int, sys.argv[1:3])
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    inherited = tuple(int(fd) for fd in sys.argv[3].split(',') if fd)
    try:
        # This single-threaded helper does no other work in the forked child.
        child = subprocess.Popen(sys.argv[4:], preexec_fn=child_signals, pass_fds=inherited)
    except OSError:
        child = None
    try:
        os.write(report, b'R')
    except BrokenPipeError:
        pass
    code = child.wait() if child is not None else 127
    try:
        os.write(report, f'{code}\n'.encode('ascii'))
    except BrokenPipeError:
        pass
    os.close(report)
    if os.read(release, 1) == b'R':
        return 0
    # Parent loss is not proof of cleanup. Keep the group identity and device
    # lock alive, including when all fixture children have already exited.
    while True:
        signal.pause()


if __name__ == '__main__':
    sys.exit(main())
