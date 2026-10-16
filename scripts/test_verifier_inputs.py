"""External helper and SDK changes invalidate retained Mobile gates."""
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('mobile_verifier_inputs', str(Path(__file__).parents[1] / 'bin/verifier-inputs'))
spec = importlib.util.spec_from_loader(loader.name, loader)
inputs = importlib.util.module_from_spec(spec)
loader.exec_module(inputs)


class VerifierInputsTests(unittest.TestCase):
    def test_sdk_package_or_tool_bytes_change_the_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / 'platform-tools/source.properties', root / 'platform-tools/adb']
            paths[0].parent.mkdir()
            for path in paths:
                path.write_text('original')
            first = inputs.file_digest(paths)
            paths[0].write_text('updated package')
            self.assertNotEqual(first, inputs.file_digest(paths))
            second = inputs.file_digest(paths)
            paths[1].write_text('updated tool')
            self.assertNotEqual(second, inputs.file_digest(paths))

    def test_dirty_or_uninitialized_external_checkout_cannot_reuse_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(inputs, 'run', side_effect=[str(root), ' M scripts/android-test-gate.py']):
                with self.assertRaises(ValueError):
                    inputs.checkout_tree(root)
            with patch.object(inputs, 'run', return_value=str(root.parent)):
                with self.assertRaises(ValueError):
                    inputs.checkout_tree(root)
            with patch.object(inputs, 'run', side_effect=[str(root), '', 'reviewed-tree']):
                self.assertEqual(inputs.checkout_tree(root), 'reviewed-tree')

    def test_missing_dependency_cannot_become_an_empty_successful_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                inputs.file_digest([Path(directory) / 'missing'])


if __name__ == '__main__':
    unittest.main()
