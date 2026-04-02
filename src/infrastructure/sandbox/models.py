"""Data models for sandboxed script execution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScriptExecutionStatus(str, Enum):
    """Supported lifecycle states for sandbox script execution."""

    PENDING = "pending"
    RUNNING = "running"
    DENIED = "denied"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass
class ScriptExecutionRequest:
    """Request payload used to execute one sandbox script."""

    skill_name: str
    script: str
    args: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30

    def __post_init__(self) -> None:
        """Validate request invariants after initialization."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")


@dataclass
class ScriptExecutionResult:
    """Result produced by sandbox script execution."""

    run_id: str
    status: ScriptExecutionStatus
    exit_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    output_files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize and validate execution status values."""
        if isinstance(self.status, ScriptExecutionStatus):
            return

        if isinstance(self.status, str):
            try:
                self.status = ScriptExecutionStatus(self.status)
            except ValueError as error:
                raise ValueError("Unsupported script execution status") from error
            return

        raise ValueError("Unsupported script execution status")


@dataclass
class ScriptPolicy:
    """Policy metadata that identifies the allowed script entry."""

    skill_name: str
    script: str
    interpreter: str
    max_timeout_seconds: float | None = None


@dataclass
class ScriptArgSchema:
    """Schema definition describing allowed arguments for scripts."""

    required_keys: list[str] = field(default_factory=list)
    allowed_keys: list[str] = field(default_factory=list)
    strict: bool = True

    def __post_init__(self) -> None:
        """Validate strict mode required/allowed key relationship."""
        if self.strict:
            required_keys_set = set(self.required_keys)
            allowed_keys_set = set(self.allowed_keys)
            if not required_keys_set.issubset(allowed_keys_set):
                raise ValueError("required_keys must be a subset of allowed_keys")
