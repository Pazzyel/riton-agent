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


def test_script_policy_rejects_non_positive_max_timeout() -> None:
    """Policy max timeout must be strictly positive."""
    with pytest.raises(ValueError, match="max_timeout_seconds must be greater than 0"):
        ScriptPolicy(allowed_skills=["demo-skill"], max_timeout_seconds=-1)


def test_script_arg_schema_rejects_required_keys_outside_allowed() -> None:
    """Strict arg schema must only require keys from allowed keys."""
    with pytest.raises(ValueError, match="required_keys must be a subset of allowed_keys"):
        ScriptArgSchema(required_keys=["missing"], allowed_keys=["name"], strict=True)


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


def test_script_policy_and_arg_schema_defaults() -> None:
    """Policy models should support safe defaults for later sandbox checks."""
    policy = ScriptPolicy(allowed_skills=["demo-skill"], max_timeout_seconds=45)
    arg_schema = ScriptArgSchema(required_keys=["name"], allowed_keys=["name", "limit"])

    assert policy.allowed_skills == ["demo-skill"]
    assert policy.max_timeout_seconds == 45
    assert policy.allow_network is False
    assert policy.allowed_read_paths == []
    assert policy.allowed_write_paths == []
    assert arg_schema.required_keys == ["name"]
    assert arg_schema.allowed_keys == ["name", "limit"]
    assert arg_schema.strict is True


def test_script_policy_rejects_required_args_outside_allowed_args() -> None:
    """Script policy should reject required args not in allowed args."""
    with pytest.raises(ValueError, match="required_args must be a subset of allowed_args"):
        ScriptPolicy(
            allowed_skills=["demo-skill"],
            max_timeout_seconds=45,
            required_args=["name"],
            allowed_args=["count"],
        )


def test_error_codes_include_sandbox_variants() -> None:
    """Error code enum should include sandbox-specific variants."""
    assert ErrorCode.SANDBOX_POLICY_VIOLATION == "SANDBOX_POLICY_VIOLATION"
    assert ErrorCode.SANDBOX_SCRIPT_TIMEOUT == "SANDBOX_SCRIPT_TIMEOUT"
    assert ErrorCode.SANDBOX_SCRIPT_EXECUTION_FAILED == "SANDBOX_SCRIPT_EXECUTION_FAILED"
