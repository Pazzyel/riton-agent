"""Service layer orchestrating sandbox execution dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import uuid
from importlib import import_module
import shutil

from config.skills_config import get_allowed_skills
from infrastructure.sandbox.audit_logger import SandboxAuditLogger
from infrastructure.sandbox.models import ScriptExecutionResult, ScriptExecutionStatus, ScriptPolicy
from infrastructure.sandbox.path_resolver import PathResolver
from infrastructure.sandbox.policy_engine import build_policy_key, scan_script_policies
from infrastructure.sandbox.local_runner import LocalRunner


class SkillScriptService:
    """Coordinate path resolution, policy checks, execution, and audit logging."""

    def __init__(
        self,
        path_resolver: PathResolver,
        allowed_skills: set[str],
        policy_map: dict[str, ScriptPolicy],
        runner: LocalRunner,
        audit_logger: SandboxAuditLogger,
    ) -> None:
        """Initialize service dependencies for sandbox orchestration."""
        self._path_resolver = path_resolver
        self._allowed_skills = allowed_skills
        self._policy_map = policy_map
        self._runner = runner
        self._audit_logger = audit_logger

    @classmethod
    def build_default(cls) -> SkillScriptService:
        """Build service with default dependencies and configured skills root."""
        # Step 1: resolve skills root from infra config, with safe fallback.
        skills_root = Path(".riton/skills")
        try:
            infra_config_module = import_module("config.infra_config")
            infra_config = infra_config_module.infra_config

            configured_path = getattr(infra_config, "skill_path", None)
            if configured_path:
                skills_root = Path(configured_path)
        except (ImportError, AttributeError, ModuleNotFoundError):
            pass

        # Step 2: load fast-lookup policy map and allowed skill whitelist.
        policy_map = scan_script_policies(skills_root)
        allowed_skills = get_allowed_skills()

        # Step 3: wire concrete dependencies for default runtime behavior.
        return cls(
            path_resolver=PathResolver(skills_root=skills_root),
            allowed_skills=allowed_skills,
            policy_map=policy_map,
            runner=LocalRunner(),
            audit_logger=SandboxAuditLogger(),
        )

    def execute_skill_script(
        self,
        skill_name: str,
        script: str,
        args: dict[str, object],
        context: dict[str, object],
    ) -> ScriptExecutionResult:
        """Execute one sandbox script and return normalized execution result."""
        run_id = uuid.uuid4().hex
        timeout_seconds, timeout_error = self._resolve_requested_timeout(context)
        normalized_script = self._normalize_script_for_lookup(script)
        if timeout_error is not None:
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail=timeout_error,
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=normalized_script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="invalid_timeout",
            )
            return denied_result

        # Step 1: deny requests for skills outside the configured allow-list.
        if skill_name not in self._allowed_skills:
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail="Skill not allowed",
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=normalized_script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="skill_not_allowed",
            )
            return denied_result

        # Step 2: require an existing policy entry for this skill/script key.
        policy_key = build_policy_key(skill_name, normalized_script)
        policy = self._policy_map.get(policy_key)
        if policy is None:
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail="No policy matched skill/script",
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=normalized_script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="policy_not_found",
            )
            return denied_result

        # Step 3: resolve script path and fail fast when path validation rejects it.
        allowed_path, resolved_path = self._path_resolver.resolve_script_path(
            skill_name,
            normalized_script,
        )
        if not allowed_path or resolved_path is None:
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail="Path resolution denied",
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=normalized_script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="path_denied",
            )
            return denied_result

        # Step 4: enforce timeout ceiling declared by the matched execution policy.
        if (
            policy.max_timeout_seconds is not None
            and timeout_seconds > policy.max_timeout_seconds
        ):
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail=(
                    "Requested timeout_seconds exceeds policy max_timeout_seconds "
                    f"({timeout_seconds} > {policy.max_timeout_seconds})"
                ),
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=normalized_script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="timeout_exceeds_policy",
            )
            return denied_result

        # Step 5: build deterministic process argv and execute via runner.
        interpreter = self._resolve_interpreter_command(policy.interpreter)
        serialized_args = json.dumps(args, separators=(",", ":"), sort_keys=True)
        argv = [interpreter, str(resolved_path), serialized_args]
        runner_result = self._runner.run(argv=argv, timeout_seconds=timeout_seconds)

        # Step 6: map runner outcome to execution lifecycle status semantics.
        if runner_result.timed_out:
            status = ScriptExecutionStatus.TIMED_OUT
        elif runner_result.exit_code == 0:
            status = ScriptExecutionStatus.COMPLETED
        else:
            status = ScriptExecutionStatus.FAILED

        reason_by_status = {
            ScriptExecutionStatus.COMPLETED: "completed",
            ScriptExecutionStatus.FAILED: "failed",
            ScriptExecutionStatus.TIMED_OUT: "timed_out",
        }

        result = ScriptExecutionResult(
            run_id=run_id,
            status=status,
            exit_code=runner_result.exit_code,
            stdout_tail=runner_result.stdout_tail,
            stderr_tail=runner_result.stderr_tail,
        )
        self._audit_run(
            run_id=run_id,
            skill_name=skill_name,
            script=normalized_script,
            status=result.status,
            exit_code=result.exit_code,
            reason=reason_by_status[result.status],
        )
        return result

    def _normalize_script_for_lookup(self, script: str) -> str:
        """Normalize script separators for stable policy and path matching."""
        return "/".join(part for part in script.replace("\\", "/").split("/") if part)

    def _resolve_interpreter_command(self, interpreter: str) -> str:
        """Resolve executable command, with python3 fallback to python when needed."""
        # Step 1: keep non-python3 interpreters unchanged by design.
        if interpreter != "python3":
            return interpreter

        # Step 2: prefer python3 when it is available on the execution host.
        if shutil.which("python3") is not None:
            return "python3"

        # Step 3: fallback to python for Windows environments lacking python3 shim.
        if shutil.which("python") is not None:
            return "python"

        # Step 4: preserve requested command when no fallback executable is discoverable.
        return interpreter

    def _resolve_requested_timeout(self, context: dict[str, object]) -> tuple[float, str | None]:
        """Parse timeout from context and return a policy-ready value or denial reason."""
        raw_timeout = context.get("timeout_seconds", 30)

        # Parse timeout in a guarded way so invalid values never raise here.
        try:
            parsed_timeout = float(raw_timeout)
        except (TypeError, ValueError):
            return 0.0, "Invalid timeout_seconds: must be a positive number"

        # Reject non-positive values explicitly to enforce baseline timeout safety.
        if parsed_timeout <= 0:
            return 0.0, "Invalid timeout_seconds: timeout_seconds must be greater than 0"

        return parsed_timeout, None

    def _audit_run(
        self,
        run_id: str,
        skill_name: str,
        script: str,
        status: ScriptExecutionStatus,
        exit_code: int | None,
        reason: str,
    ) -> None:
        """Write one normalized run summary through the audit logger."""
        self._audit_logger.log_run_summary(
            {
                "run_id": run_id,
                "skill_name": skill_name,
                "script": script,
                "status": status.value,
                "exit_code": exit_code,
                "reason": reason,
            }
        )
