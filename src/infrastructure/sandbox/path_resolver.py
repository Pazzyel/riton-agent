"""Path resolution utilities for sandbox script execution."""

from pathlib import Path
from pathlib import PureWindowsPath


class PathResolver:
    """Resolve skill script paths while enforcing sandbox boundaries."""

    def __init__(self, skills_root: Path) -> None:
        """Initialize resolver with the root directory for all skills."""
        self._skills_root: Path = skills_root.resolve()

    def _is_windows_absolute(self, value: str) -> bool:
        """Return whether path uses an absolute Windows-style form."""
        # 检测是否是Windows平台上的绝对地址，是也禁止调用
        windows_path = PureWindowsPath(value)
        return bool(windows_path.drive) or windows_path.is_absolute()

    def _is_valid_skill_name(self, skill_name: str) -> bool:
        """Return whether skill name is one safe single path segment."""
        skill_path = Path(skill_name)
        if skill_path.is_absolute() or self._is_windows_absolute(skill_name):
            return False

        # 禁止 .. 逃逸到其它路径
        parts = skill_path.parts
        if ".." in parts or len(parts) != 1:
            return False

        return True

    def resolve_script_path(self, skill_name: str, script: str) -> tuple[bool, Path | None]:
        """Return whether script is allowed and the resolved path when allowed."""
        if not self._is_valid_skill_name(skill_name):
            return False, None

        if Path(script).is_absolute() or self._is_windows_absolute(script):
            return False, None

        if ".." in Path(script).parts:
            return False, None

        # Build and normalize the script location under skills root.
        candidate_path: Path = (self._skills_root / skill_name / script).resolve()

        # Deny any path that resolves outside the configured root boundary.
        try:
            candidate_path.relative_to(self._skills_root)
        except ValueError:
            return False, None

        return True, candidate_path
