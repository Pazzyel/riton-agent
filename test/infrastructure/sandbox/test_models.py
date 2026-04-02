from pathlib import Path
import sys

import pytest


def _prepare_src_import_path() -> None:
    """Ensure tests can import modules from the src directory."""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_prepare_src_import_path()

from common.exceptions import ErrorCode
from infrastructure.sandbox.models import (
    ScriptArgSchema,
    ScriptExecutionRequest,
    ScriptExecutionResult,
    ScriptExecutionStatus,
    ScriptPolicy,
)


def test_script_execution_request_defaults() -> None:
    """Script execution request should default timeout and empty dictionaries."""
    request = ScriptExecutionRequest(skill_name="demo", script="run.py")

    assert request.skill_name == "demo"
    assert request.script == "run.py"
    assert request.args == {}
    assert request.context == {}
    assert request.timeout_seconds == 30


def test_script_execution_result_defaults() -> None:
    """Script execution result should default optional fields safely."""
    result = ScriptExecutionResult(run_id="run-1", status="completed")

    assert result.run_id == "run-1"
    assert result.status is ScriptExecutionStatus.COMPLETED
    assert result.exit_code is None
    assert result.stdout_tail == ""
    assert result.stderr_tail == ""
    assert result.output_files == []


def test_script_execution_request_rejects_non_positive_timeout() -> None:
    """Execution request timeout must be strictly positive."""
    with pytest.raises(ValueError, match="timeout_seconds must be greater than 0"):
        ScriptExecutionRequest(skill_name="demo", script="run.py", timeout_seconds=0)


def test_script_policy_fields_are_minimal() -> None:
    """Script policy should expose core fields with optional timeout unset."""
    policy = ScriptPolicy(skill_name="demo-skill", script="run.py", interpreter="python")

    assert policy.skill_name == "demo-skill"
    assert policy.script == "run.py"
    assert policy.interpreter == "python"
    assert policy.max_timeout_seconds is None


def test_script_policy_allows_optional_max_timeout() -> None:
    """Script policy should allow configuring an optional max timeout."""
    policy = ScriptPolicy(
        skill_name="demo-skill",
        script="run.py",
        interpreter="python",
        max_timeout_seconds=12.5,
    )

    assert policy.max_timeout_seconds == 12.5


def test_script_arg_schema_rejects_required_keys_outside_allowed() -> None:
    """Strict arg schema must only require keys from allowed keys."""
    with pytest.raises(ValueError, match="required_keys must be a subset of allowed_keys"):
        ScriptArgSchema(required_keys=["missing"], allowed_keys=["name"], strict=True)


def test_script_arg_schema_rejects_required_keys_when_allowed_is_empty() -> None:
    """Strict arg schema should enforce subset relationship for empty allowlists."""
    with pytest.raises(ValueError, match="required_keys must be a subset of allowed_keys"):
        ScriptArgSchema(required_keys=["missing"], allowed_keys=[], strict=True)


def test_script_arg_schema_allows_any_required_keys_when_non_strict() -> None:
    """Non-strict arg schema should not enforce subset relationship."""
    schema = ScriptArgSchema(required_keys=["missing"], allowed_keys=["name"], strict=False)

    assert schema.required_keys == ["missing"]


def test_script_execution_result_accepts_enum_status() -> None:
    """Execution result should preserve enum status inputs."""
    result = ScriptExecutionResult(run_id="run-2", status=ScriptExecutionStatus.RUNNING)

    assert result.status is ScriptExecutionStatus.RUNNING


def test_script_execution_result_rejects_unknown_status() -> None:
    """Execution result should reject unsupported status values."""
    with pytest.raises(ValueError, match="Unsupported script execution status"):
        ScriptExecutionResult(run_id="run-3", status="unknown")


def test_script_execution_result_rejects_non_string_non_enum_status() -> None:
    """Execution result should reject status values that are neither strings nor enums."""
    with pytest.raises(ValueError, match="Unsupported script execution status"):
        ScriptExecutionResult(run_id="run-4", status=123)  # type: ignore[arg-type]


def test_script_arg_schema_defaults() -> None:
    """Argument schema should keep strict mode and supplied key sets."""
    arg_schema = ScriptArgSchema(required_keys=["name"], allowed_keys=["name", "limit"])

    assert arg_schema.required_keys == ["name"]
    assert arg_schema.allowed_keys == ["name", "limit"]
    assert arg_schema.strict is True


def test_error_codes_include_sandbox_variants() -> None:
    """Error code enum should include sandbox-specific variants."""
    assert ErrorCode.SANDBOX_POLICY_VIOLATION == "SANDBOX_POLICY_VIOLATION"
    assert ErrorCode.SANDBOX_SCRIPT_TIMEOUT == "SANDBOX_SCRIPT_TIMEOUT"
    assert ErrorCode.SANDBOX_SCRIPT_EXECUTION_FAILED == "SANDBOX_SCRIPT_EXECUTION_FAILED"
