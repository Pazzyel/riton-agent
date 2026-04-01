from pathlib import Path
import subprocess
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

from infrastructure.sandbox.local_runner import LocalRunner


def test_local_runner_executes_with_shell_disabled(monkeypatch: object) -> None:
    """Runner should execute subprocess calls with shell disabled."""
    runner = LocalRunner()

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["shell"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="out", stderr="err")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = runner.run([sys.executable, "-c", "print('ok')"], timeout_seconds=1)

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.stdout_tail == "out"
    assert result.stderr_tail == "err"


def test_local_runner_captures_stdout_stderr_and_exit_code() -> None:
    """Runner should capture process output streams and exit code."""
    runner = LocalRunner()

    result = runner.run(
        [
            sys.executable,
            "-c",
            "import sys; print('hello-out'); print('hello-err', file=sys.stderr); sys.exit(7)",
        ],
        timeout_seconds=2,
    )

    assert result.exit_code == 7
    assert result.timed_out is False
    assert "hello-out" in result.stdout_tail
    assert "hello-err" in result.stderr_tail
    assert result.duration_ms >= 0


def test_local_runner_truncates_output_tails_to_last_2000_characters() -> None:
    """Runner should keep only the last 2000 characters for each stream tail."""
    runner = LocalRunner()
    stdout_payload = "A" * 2500
    stderr_payload = "B" * 2500

    result = runner.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.stdout.write('{stdout_payload}'); "
                f"sys.stderr.write('{stderr_payload}')"
            ),
        ],
        timeout_seconds=2,
    )

    assert result.timed_out is False
    assert result.exit_code == 0
    assert len(result.stdout_tail) == 2000
    assert len(result.stderr_tail) == 2000
    assert result.stdout_tail == stdout_payload[-2000:]
    assert result.stderr_tail == stderr_payload[-2000:]


def test_local_runner_marks_timeout_and_clears_exit_code() -> None:
    """Runner should flag timeouts and return no exit code when timed out."""
    runner = LocalRunner()

    result = runner.run(
        [sys.executable, "-c", "import time; time.sleep(1)"] ,
        timeout_seconds=0.1,
    )

    assert result.timed_out is True
    assert result.exit_code is None
    assert result.duration_ms >= 0
