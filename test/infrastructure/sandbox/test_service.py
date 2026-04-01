from pathlib import Path
import sys
from types import ModuleType


def _prepare_src_import_path() -> None:
    """Ensure tests can import modules from the src directory."""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_prepare_src_import_path()

from infrastructure.sandbox.models import ScriptExecutionStatus, ScriptPolicy
from infrastructure.sandbox.local_runner import RunnerResult
from infrastructure.sandbox.skill_script_service import SkillScriptService


class _PathResolverStub:
    """Stub resolver returning a preconfigured path decision."""

    def __init__(self, allowed: bool, resolved_path: Path | None) -> None:
        """Store resolver decision used by tests."""
        self.allowed = allowed
        self.resolved_path = resolved_path
        self.calls: list[tuple[str, str]] = []

    def resolve_script_path(self, skill_name: str, script: str) -> tuple[bool, Path | None]:
        """Return configured path resolution result."""
        self.calls.append((skill_name, script))
        return self.allowed, self.resolved_path


class _PolicyEngineStub:
    """Stub policy engine returning a preconfigured decision."""

    def __init__(
        self,
        allowed: bool,
        reason: str,
        matched_policy: ScriptPolicy | None = None,
    ) -> None:
        """Store policy decision used by tests."""
        self.allowed = allowed
        self.reason = reason
        self.matched_policy = matched_policy
        self.calls: list[tuple[str, str, str, dict[str, object]]] = []

    def evaluate(
        self,
        skill_name: str,
        script: str,
        interpreter: str,
        args: dict[str, object],
    ) -> tuple[bool, str]:
        """Return configured policy evaluation result."""
        self.calls.append((skill_name, script, interpreter, args))
        return self.allowed, self.reason

    def evaluate_with_policy(
        self,
        skill_name: str,
        script: str,
        interpreter: str,
        args: dict[str, object],
    ) -> tuple[bool, str, ScriptPolicy | None]:
        """Return configured policy decision plus matched policy details."""
        self.calls.append((skill_name, script, interpreter, args))
        return self.allowed, self.reason, self.matched_policy


class _RunnerStub:
    """Stub runner that records argv and timeout calls."""

    def __init__(self, result: RunnerResult) -> None:
        """Store runner result used by tests."""
        self.result = result
        self.calls: list[tuple[list[str], float]] = []

    def run(self, argv: list[str], timeout_seconds: float) -> RunnerResult:
        """Record invocation and return the configured result."""
        self.calls.append((argv, timeout_seconds))
        return self.result


class _AuditLoggerStub:
    """Stub audit logger collecting run summaries."""

    def __init__(self) -> None:
        """Initialize empty audit summary collection."""
        self.summaries: list[dict[str, object]] = []

    def log_run_summary(self, summary: dict[str, object]) -> None:
        """Record one audit summary entry."""
        self.summaries.append(summary)


def _build_policy() -> ScriptPolicy:
    """Create a baseline policy for build_default tests."""
    return ScriptPolicy(
        allowed_skills=["skill-a"],
        max_timeout_seconds=30,
        skill_name="skill-a",
        script="scripts/run.py",
        interpreter="python",
    )


def test_execute_denies_when_path_resolution_fails() -> None:
    """Service should deny execution when path resolution is rejected."""
    path_resolver = _PathResolverStub(allowed=False, resolved_path=None)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok")
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "Path resolution denied" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_policy_engine_rejects_request() -> None:
    """Service should deny execution when policy evaluation fails."""
    path = Path("/tmp/fake.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=path)
    policy_engine = _PolicyEngineStub(allowed=False, reason="policy denied")
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "policy denied" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_timeout_value_is_invalid() -> None:
    """Service should deny execution when timeout value cannot be parsed."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok")
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script(
        "skill-a",
        "scripts/run.py",
        {"name": "alex"},
        {"timeout_seconds": "not-a-number"},
    )

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "Invalid timeout_seconds" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_timeout_is_non_positive() -> None:
    """Service should deny execution when timeout value is non-positive."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok")
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script(
        "skill-a",
        "scripts/run.py",
        {"name": "alex"},
        {"timeout_seconds": 0},
    )

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "timeout_seconds must be greater than 0" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_timeout_exceeds_policy_max() -> None:
    """Service should deny execution when timeout exceeds policy maximum."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    matched_policy = ScriptPolicy(
        allowed_skills=["skill-a"],
        max_timeout_seconds=5,
        skill_name="skill-a",
        script="scripts/run.py",
        interpreter="python",
    )
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok", matched_policy=matched_policy)
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script(
        "skill-a",
        "scripts/run.py",
        {"name": "alex"},
        {"timeout_seconds": 9},
    )

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "exceeds policy max_timeout_seconds" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_runs_interpreter_script_and_serialized_args() -> None:
    """Service should run interpreter and script with serialized arguments."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok")
    runner = _RunnerStub(
        RunnerResult(
            exit_code=0,
            timed_out=False,
            stdout_tail="done",
            stderr_tail="",
            duration_ms=3,
        )
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script(
        "skill-a",
        "scripts/run.py",
        {"count": 2, "name": "alex"},
        {"interpreter": "python3", "timeout_seconds": 9},
    )

    assert result.status is ScriptExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert result.stdout_tail == "done"
    assert policy_engine.calls[0][2] == "python3"
    assert runner.calls[0][0] == [
        "python3",
        str(script_path),
        '{"count":2,"name":"alex"}',
    ]
    assert runner.calls[0][1] == 9
    assert len(audit_logger.summaries) == 1


def test_execute_maps_timeout_to_timed_out_status() -> None:
    """Service should map runner timeout to timed out execution status."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok")
    runner = _RunnerStub(
        RunnerResult(
            exit_code=None,
            timed_out=True,
            stdout_tail="",
            stderr_tail="timeout",
            duration_ms=1000,
        )
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {}, {})

    assert result.status is ScriptExecutionStatus.TIMED_OUT
    assert result.exit_code is None
    assert len(audit_logger.summaries) == 1


def test_execute_maps_non_zero_exit_to_failed_status() -> None:
    """Service should map non-zero runner exit code to failed status."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy_engine = _PolicyEngineStub(allowed=True, reason="ok")
    runner = _RunnerStub(
        RunnerResult(
            exit_code=17,
            timed_out=False,
            stdout_tail="",
            stderr_tail="bad run",
            duration_ms=11,
        )
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, policy_engine, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {}, {})

    assert result.status is ScriptExecutionStatus.FAILED
    assert result.exit_code == 17
    assert len(audit_logger.summaries) == 1


def test_build_default_falls_back_to_dot_riton_skills(monkeypatch: object) -> None:
    """build_default should use .riton/skills when infra config is unavailable."""
    monkeypatch.delitem(sys.modules, "config", raising=False)
    monkeypatch.delitem(sys.modules, "config.infra_config", raising=False)

    service = SkillScriptService.build_default([_build_policy()])

    assert service._path_resolver._skills_root == Path(".riton/skills").resolve()


def test_build_default_prefers_configured_skill_path(monkeypatch: object, tmp_path: Path) -> None:
    """build_default should prefer config.infra_config.skill_path when present."""
    config_module = ModuleType("config")
    infra_config_module = ModuleType("config.infra_config")

    class _InfraConfig:
        """Minimal config object for testing configured skill path."""

        def __init__(self, skill_path: str) -> None:
            """Store configured skill path."""
            self.skill_path = skill_path

    infra_config_module.infra_config = _InfraConfig(str(tmp_path / "skills-root"))
    monkeypatch.setitem(sys.modules, "config", config_module)
    monkeypatch.setitem(sys.modules, "config.infra_config", infra_config_module)

    service = SkillScriptService.build_default([_build_policy()])

    assert service._path_resolver._skills_root == (tmp_path / "skills-root").resolve()
