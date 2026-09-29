"""The dispatcher status must distinguish a dead PID from denied inspection."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class StatusTests(unittest.TestCase):
    def status(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            (root / "target").mkdir()
            (root / "fake").mkdir()
            shutil.copy2(Path(__file__).with_name("pyry-status"), root / "bin/pyry-status")
            (root / "target/.dispatcher.lock").write_text("PID=1234\n")
            ps = root / "fake/ps"
            ps.write_text(
                '#!/bin/sh\n'
                'case "$*" in *"pid="*)\n'
                '  case "$TEST_PS_MODE" in\n'
                '    alive) echo 1234; exit 0;;\n'
                '    dead) exit 1;;\n'
                '    denied) echo "operation not permitted" >&2; exit 1;;\n'
                '  esac\n'
                '  ;; esac\n'
                'case "$*" in\n'
                '  *"command="*) echo /opt/homebrew/bin/node;;\n'
                '  *"lstart="*) echo "Tue Sep 29 18:04:39 2026";;\n'
                'esac\n'
            )
            ps.chmod(0o755)
            env = dict(
                os.environ,
                PATH=str(root / "fake") + os.pathsep + os.environ["PATH"],
                TARGET_REPO_PATH=str(root / "target"),
                TEST_PS_MODE=mode,
            )
            return subprocess.run(
                ["sh", str(root / "bin/pyry-status")], env=env, capture_output=True, text=True
            )

    def test_running_process(self):
        result = self.status("alive")
        self.assertEqual(result.returncode, 0)
        self.assertIn("running   pid=1234", result.stdout)

    def test_dead_process(self):
        result = self.status("dead")
        self.assertEqual(result.returncode, 1)
        self.assertIn("stopped (stale lock", result.stdout)

    def test_denied_inspection_is_unknown(self):
        result = self.status("denied")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown (process inspection failed", result.stdout)
        self.assertNotIn("stopped", result.stdout)


if __name__ == "__main__":
    unittest.main()
