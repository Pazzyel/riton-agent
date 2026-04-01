"""Smoke test for the sandbox example runner."""

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

from infrastructure.sandbox.example import run_example


def test_run_example_returns_expected_result_shape() -> None:
    """run_example should execute demo script and return normalized fields."""
    result = run_example()

    assert set(result.keys()) == {
        "run_id",
        "status",
        "exit_code",
        "stdout_tail",
        "stderr_tail",
        "output_files",
    }
    assert isinstance(result["run_id"], str)
    assert result["run_id"]
    assert isinstance(result["status"], str)
    assert result["status"] == "completed"
    assert result["exit_code"] == 0
    assert isinstance(result["stdout_tail"], str)
    assert "echo_args" in result["stdout_tail"]
    assert isinstance(result["stderr_tail"], str)
    assert result["stderr_tail"] == ""
    assert isinstance(result["output_files"], list)
