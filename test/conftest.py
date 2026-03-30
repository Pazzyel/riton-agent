import sys
from pathlib import Path


def _ensure_src_import_path() -> None:
    """Ensure project root is available for `src.*` imports in tests."""
    test_dir: Path = Path(__file__).resolve().parent
    project_root: Path = test_dir.parent
    project_root_str: str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


_ensure_src_import_path()
