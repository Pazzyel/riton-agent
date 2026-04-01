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
        if isinstance(self.status, str):
            try:
                self.status = ScriptExecutionStatus(self.status)
            except ValueError as error:
                raise ValueError("Unsupported script execution status") from error


@dataclass
class ScriptPolicy:
    """Policy constraints that control sandbox script permissions."""

    allowed_skills: list[str]
    max_timeout_seconds: int
    allow_network: bool = False
    allowed_read_paths: list[str] = field(default_factory=list)
    allowed_write_paths: list[str] = field(default_factory=list)
    skill_name: str | None = None
    script: str | None = None
    interpreter: str | None = None
    required_args: list[str] = field(default_factory=list)
    allowed_args: list[str] = field(default_factory=list)
    arg_types: dict[str, type[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate policy timeout and argument constraints."""
        if self.max_timeout_seconds <= 0:
            raise ValueError("max_timeout_seconds must be greater than 0")

        if self.allowed_args:
            required_args_set = set(self.required_args)
            allowed_args_set = set(self.allowed_args)
            if not required_args_set.issubset(allowed_args_set):
                raise ValueError("required_args must be a subset of allowed_args")


@dataclass
class ScriptArgSchema:
    """Schema definition describing allowed arguments for scripts."""

    required_keys: list[str] = field(default_factory=list)
    allowed_keys: list[str] = field(default_factory=list)
    strict: bool = True

    def __post_init__(self) -> None:
        """Validate strict mode required/allowed key relationship."""
        if self.strict and self.allowed_keys:
            required_keys_set = set(self.required_keys)
            allowed_keys_set = set(self.allowed_keys)
            if not required_keys_set.issubset(allowed_keys_set):
                raise ValueError("required_keys must be a subset of allowed_keys")
