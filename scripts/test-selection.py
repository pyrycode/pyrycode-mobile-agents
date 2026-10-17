"""Load the shared selection policy from this consumer's pinned dispatcher."""
import importlib.util
from pathlib import Path


def check_selection(root, kind, args, env=None):
    policy = Path(__file__).resolve().parents[1] / 'dispatcher/scripts/test-selection.py'
    try:
        spec = importlib.util.spec_from_file_location('pyry_mobile_selection_policy', policy)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.check(Path(root), kind, list(args), env)
    except (OSError, ValueError) as error:
        raise SystemExit(f'Test selection: {error}') from error
