"""Local process runner for sandbox command execution."""

from dataclasses import dataclass
import subprocess
import time


@dataclass
class RunnerResult:
    """Execution result returned by a runner invocation."""

    exit_code: int | None
    timed_out: bool
    stdout_tail: str
    stderr_tail: str
    duration_ms: int


def _truncate_tail(value: str, max_chars: int = 2000) -> str:
    """Return the last ``max_chars`` of a text value."""
    return value[-max_chars:]


def _normalize_text(value: str | bytes | None) -> str:
    """Normalize subprocess output values to a string."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


class LocalRunner:
    """Run local commands with timeout and output capture."""

    def run(self, argv: list[str], timeout_seconds: float) -> RunnerResult:
        """Execute command arguments and return normalized execution details."""
        # 直接执行脚本
        # Step 1: capture start time before invocation for accurate duration.
        started_at = time.perf_counter()

        try:
            # Step 2: execute process with explicit non-shell mode and captured text output.
            completed = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout = _normalize_text(completed.stdout)
            stderr = _normalize_text(completed.stderr)
            exit_code: int | None = completed.returncode
            timed_out = False
        except subprocess.TimeoutExpired as error:
            # Step 3: mark timeout and preserve any partial output from the exception.
            stdout = _normalize_text(error.stdout)
            stderr = _normalize_text(error.stderr)
            exit_code = None
            timed_out = True

        # Step 4: compute elapsed duration and trim output tails to fixed size.
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return RunnerResult(
            exit_code=exit_code,
            timed_out=timed_out,
            stdout_tail=_truncate_tail(stdout),
            stderr_tail=_truncate_tail(stderr),
            duration_ms=duration_ms,
        )
