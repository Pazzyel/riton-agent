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

from infrastructure.sandbox.path_resolver import PathResolver


def test_resolve_rejects_absolute_script_path(tmp_path: Path) -> None:
    """Resolver should deny absolute script paths."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("demo-skill", "/bin/run.py")

    assert allowed is False
    assert resolved_path is None


def test_resolve_rejects_parent_traversal_in_script(tmp_path: Path) -> None:
    """Resolver should deny script paths containing parent traversal."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("demo-skill", "../run.py")

    assert allowed is False
    assert resolved_path is None


def test_resolve_returns_resolved_path_under_skills_root(tmp_path: Path) -> None:
    """Resolver should resolve relative script under skill folder."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("demo-skill", "scripts/run.py")

    assert allowed is True
    assert resolved_path == (tmp_path / "demo-skill" / "scripts" / "run.py").resolve()


def test_resolve_denies_paths_escaping_skills_root_via_skill_name(tmp_path: Path) -> None:
    """Resolver should deny paths that escape root after resolution."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("..", "outside.py")

    assert allowed is False
    assert resolved_path is None


def test_resolve_rejects_nested_parent_traversal_component(tmp_path: Path) -> None:
    """Resolver should deny traversal even when nested in script path."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("demo-skill", "scripts/../run.py")

    assert allowed is False
    assert resolved_path is None


def test_resolve_rejects_skill_name_with_parent_traversal(tmp_path: Path) -> None:
    """Resolver should deny skill names containing traversal segments."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("a/../b", "run.py")

    assert allowed is False
    assert resolved_path is None


def test_resolve_rejects_nested_skill_name_segments(tmp_path: Path) -> None:
    """Resolver should only allow single-segment skill names."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("nested/name", "run.py")

    assert allowed is False
    assert resolved_path is None


def test_resolve_rejects_windows_drive_script_forms(tmp_path: Path) -> None:
    """Resolver should deny Windows drive-based absolute script forms."""
    resolver = PathResolver(tmp_path)

    for script in ("C:/Windows/System32/cmd.exe", "C:\\Windows\\System32\\cmd.exe"):
        allowed, resolved_path = resolver.resolve_script_path("demo-skill", script)
        assert allowed is False
        assert resolved_path is None


def test_resolve_normalizes_backslash_script_separators(tmp_path: Path) -> None:
    """Resolver should treat backslash script separators as normal path separators."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("demo-skill", r"scripts\nested\run.py")

    assert allowed is True
    assert resolved_path == (tmp_path / "demo-skill" / "scripts" / "nested" / "run.py").resolve()


def test_resolve_rejects_backslash_parent_traversal(tmp_path: Path) -> None:
    """Resolver should deny parent traversal even when using backslashes."""
    resolver = PathResolver(tmp_path)

    allowed, resolved_path = resolver.resolve_script_path("demo-skill", r"scripts\..\run.py")

    assert allowed is False
    assert resolved_path is None
