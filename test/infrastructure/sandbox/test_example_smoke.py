"""Smoke test for the sandbox example runner."""

from pathlib import Path
import os


def test_run_example_returns_expected_result_shape(monkeypatch) -> None:
    """run_example should execute demo script and return normalized fields."""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    monkeypatch.syspath_prepend(str(src_root))

    def _deny_chdir(_: str | os.PathLike[str]) -> None:
        raise AssertionError("run_example must not call os.chdir")

    monkeypatch.setattr(os, "chdir", _deny_chdir)

    from infrastructure.sandbox.example import run_example

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
