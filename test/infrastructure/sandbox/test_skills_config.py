from pathlib import Path
import sys


def _prepare_src_import_path() -> None:
    """Ensure tests can import modules from the src directory."""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_prepare_src_import_path()

from config.skills_config import get_allowed_skills


def test_get_allowed_skills_returns_default_set() -> None:
    """get_allowed_skills should return the built-in default skill whitelist."""
    assert get_allowed_skills() == {"demo", "shell-script", "python-script"}


def test_get_allowed_skills_reads_env_override(monkeypatch) -> None:
    """get_allowed_skills should allow overriding defaults through env."""
    monkeypatch.setenv("RITON_ALLOWED_SKILLS", "alpha,beta,alpha")

    assert get_allowed_skills() == {"alpha", "beta"}


def test_get_allowed_skills_ignores_blank_env_entries(monkeypatch) -> None:
    """get_allowed_skills should drop empty entries in override values."""
    monkeypatch.setenv("RITON_ALLOWED_SKILLS", " alpha, , beta ,, ")

    assert get_allowed_skills() == {"alpha", "beta"}
