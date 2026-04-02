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

    def _normalize_script_path(self, script: str) -> Path:
        """Return script path normalized to forward-slash segment semantics."""
        normalized_script = "/".join(part for part in script.replace("\\", "/").split("/") if part)
        return Path(normalized_script)

    def _is_rooted_without_drive(self, script: str) -> bool:
        """Return whether script is rooted (/, \\) even without a drive letter."""
        return script.startswith(("/", "\\"))

    def resolve_script_path(self, skill_name: str, script: str) -> tuple[bool, Path | None]:
        """Return whether script is allowed and the resolved path when allowed."""
        # Step 1: reject malformed skill names before any script processing.
        if not self._is_valid_skill_name(skill_name):
            return False, None

        # Step 2: deny absolute or rooted script forms in both POSIX and Windows styles.
        if (
            Path(script).is_absolute()
            or self._is_windows_absolute(script)
            or self._is_rooted_without_drive(script)
        ):
            return False, None

        # Step 3: normalize separators first so traversal checks are platform-consistent.
        normalized_script = self._normalize_script_path(script)

        if ".." in normalized_script.parts:
            return False, None

        # Step 4: resolve target path and enforce containment under sandbox skills root.
        candidate_path: Path = (self._skills_root / skill_name / normalized_script).resolve()

        # Deny any path that resolves outside the configured root boundary.
        try:
            candidate_path.relative_to(self._skills_root)
        except ValueError:
            return False, None

        return True, candidate_path
