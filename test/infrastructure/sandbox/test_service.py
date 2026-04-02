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
from infrastructure.sandbox.policy_engine import build_policy_key
from infrastructure.sandbox.local_runner import RunnerResult
import infrastructure.sandbox.skill_script_service as skill_script_service_module
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
        skill_name="skill-a",
        script="scripts/run.py",
        interpreter="python",
    )


def test_execute_denies_when_path_resolution_fails() -> None:
    """Service should deny execution when path resolution is rejected."""
    path_resolver = _PathResolverStub(allowed=False, resolved_path=None)
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): _build_policy()}, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "Path resolution denied" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_policy_engine_rejects_request() -> None:
    """Service should deny execution when skill is not allowed."""
    path = Path("/tmp/fake.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=path)
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, set(), {build_policy_key("skill-a", "scripts/run.py"): _build_policy()}, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "Skill not allowed" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_policy_key_missing() -> None:
    """Service should deny execution when no policy map entry exists."""
    path = Path("/tmp/fake.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=path)
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, {"skill-a"}, {}, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.DENIED
    assert result.exit_code is None
    assert "No policy matched skill/script" in result.stderr_tail
    assert runner.calls == []
    assert len(audit_logger.summaries) == 1


def test_execute_denies_when_timeout_value_is_invalid() -> None:
    """Service should deny execution when timeout value cannot be parsed."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): _build_policy()}, runner, audit_logger)

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
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): _build_policy()}, runner, audit_logger)

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
        skill_name="skill-a",
        script="scripts/run.py",
        interpreter="python",
        max_timeout_seconds=5,
    )
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="", stderr_tail="", duration_ms=1)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): matched_policy}, runner, audit_logger)

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
    policy = ScriptPolicy(skill_name="skill-a", script="scripts/run.py", interpreter="python3")
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
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): policy}, runner, audit_logger)

    result = service.execute_skill_script(
        "skill-a",
        "scripts/run.py",
        {"count": 2, "name": "alex"},
        {"interpreter": "python", "timeout_seconds": 9},
    )

    assert result.status is ScriptExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert result.stdout_tail == "done"
    assert runner.calls[0][0] == [
        "python3",
        str(script_path),
        '{"count":2,"name":"alex"}',
    ]
    assert runner.calls[0][1] == 9
    assert len(audit_logger.summaries) == 1
    assert audit_logger.summaries[0]["reason"] == "completed"


def test_execute_maps_timeout_to_timed_out_status() -> None:
    """Service should map runner timeout to timed out execution status."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
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
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): _build_policy()}, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {}, {})

    assert result.status is ScriptExecutionStatus.TIMED_OUT
    assert result.exit_code is None
    assert len(audit_logger.summaries) == 1
    assert audit_logger.summaries[0]["reason"] == "timed_out"


def test_execute_maps_non_zero_exit_to_failed_status() -> None:
    """Service should map non-zero runner exit code to failed status."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
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
    service = SkillScriptService(path_resolver, {"skill-a"}, {build_policy_key("skill-a", "scripts/run.py"): _build_policy()}, runner, audit_logger)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {}, {})

    assert result.status is ScriptExecutionStatus.FAILED
    assert result.exit_code == 17
    assert len(audit_logger.summaries) == 1
    assert audit_logger.summaries[0]["reason"] == "failed"


def test_execute_falls_back_to_python_when_python3_unavailable(
    monkeypatch: object,
) -> None:
    """Service should run python when policy prefers unavailable python3."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy = ScriptPolicy(skill_name="skill-a", script="scripts/run.py", interpreter="python3")
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="ok", stderr_tail="", duration_ms=2)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(
        path_resolver,
        {"skill-a"},
        {build_policy_key("skill-a", "scripts/run.py"): policy},
        runner,
        audit_logger,
    )

    def _fake_which(command: str) -> str | None:
        """Return only python executable path for interpreter resolution tests."""
        if command == "python3":
            return None
        if command == "python":
            return "/usr/bin/python"
        return None

    monkeypatch.setattr(skill_script_service_module.shutil, "which", _fake_which)

    result = service.execute_skill_script("skill-a", "scripts/run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.COMPLETED
    assert runner.calls[0][0][0] == "python"


def test_execute_normalizes_script_path_before_policy_and_path_resolution() -> None:
    """Service should normalize script separators before lookups and path checks."""
    script_path = Path("/sandbox/skill-a/scripts/run.py")
    path_resolver = _PathResolverStub(allowed=True, resolved_path=script_path)
    policy = ScriptPolicy(skill_name="skill-a", script="scripts/run.py", interpreter="python3")
    runner = _RunnerStub(
        RunnerResult(exit_code=0, timed_out=False, stdout_tail="ok", stderr_tail="", duration_ms=2)
    )
    audit_logger = _AuditLoggerStub()
    service = SkillScriptService(
        path_resolver,
        {"skill-a"},
        {build_policy_key("skill-a", "scripts/run.py"): policy},
        runner,
        audit_logger,
    )

    result = service.execute_skill_script("skill-a", r"scripts\run.py", {"name": "alex"}, {})

    assert result.status is ScriptExecutionStatus.COMPLETED
    assert path_resolver.calls == [("skill-a", "scripts/run.py")]


def test_build_default_falls_back_to_dot_riton_skills(monkeypatch: object) -> None:
    """build_default should use .riton/skills when infra config is unavailable."""
    monkeypatch.delitem(sys.modules, "config", raising=False)
    monkeypatch.delitem(sys.modules, "config.infra_config", raising=False)
    monkeypatch.setattr(skill_script_service_module, "scan_script_policies", lambda skills_root: {})

    monkeypatch.setattr(skill_script_service_module, "get_allowed_skills", lambda: {"skill-a"})

    service = SkillScriptService.build_default()

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
    monkeypatch.setattr(skill_script_service_module, "get_allowed_skills", lambda: {"skill-a"})
    monkeypatch.setattr(skill_script_service_module, "scan_script_policies", lambda skills_root: {})

    service = SkillScriptService.build_default()

    assert service._path_resolver._skills_root == (tmp_path / "skills-root").resolve()


def test_build_default_loads_allowed_skills_and_policy_map(
    monkeypatch: object, tmp_path: Path
) -> None:
    """build_default should load allowed skills and scanned policy map."""
    config_module = ModuleType("config")
    infra_config_module = ModuleType("config.infra_config")

    class _InfraConfig:
        """Minimal config object for testing configured skill path."""

        def __init__(self, skill_path: str) -> None:
            """Store configured skill path."""
            self.skill_path = skill_path

    scanned_policy = ScriptPolicy(
        skill_name="skill-b",
        script="scripts/run.py",
        interpreter="python3",
    )
    policy_map = {build_policy_key("skill-b", "scripts/run.py"): scanned_policy}

    infra_config_module.infra_config = _InfraConfig(str(tmp_path / "skills-root"))
    monkeypatch.setitem(sys.modules, "config", config_module)
    monkeypatch.setitem(sys.modules, "config.infra_config", infra_config_module)
    monkeypatch.setattr(skill_script_service_module, "get_allowed_skills", lambda: {"skill-b"})
    monkeypatch.setattr(skill_script_service_module, "scan_script_policies", lambda skills_root: policy_map)

    service = SkillScriptService.build_default()

    assert service._allowed_skills == {"skill-b"}
    assert service._policy_map == policy_map


def test_build_default_executes_demo_with_default_allowlist(monkeypatch: object) -> None:
    """build_default should run demo script when default allowlist is active."""
    monkeypatch.delenv("RITON_ALLOWED_SKILLS", raising=False)

    service = SkillScriptService.build_default()
    result = service.execute_skill_script(
        "demo",
        "scripts/echo_args.py",
        {"message": "hello from test", "count": 1},
        {"timeout_seconds": 10},
    )

    assert result.status in {
        ScriptExecutionStatus.COMPLETED,
        ScriptExecutionStatus.FAILED,
    }
    assert result.status is not ScriptExecutionStatus.DENIED
