"""Service layer orchestrating sandbox execution dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import uuid

from infrastructure.sandbox.audit_logger import SandboxAuditLogger
from infrastructure.sandbox.models import ScriptExecutionResult, ScriptExecutionStatus, ScriptPolicy
from infrastructure.sandbox.path_resolver import PathResolver
from infrastructure.sandbox.policy_engine import PolicyEngine
from infrastructure.sandbox.local_runner import LocalRunner


class SkillScriptService:
    """Coordinate path resolution, policy checks, execution, and audit logging."""

    def __init__(
        self,
        path_resolver: PathResolver,
        policy_engine: PolicyEngine,
        runner: LocalRunner,
        audit_logger: SandboxAuditLogger,
    ) -> None:
        """Initialize service dependencies for sandbox orchestration."""
        self._path_resolver = path_resolver
        self._policy_engine = policy_engine
        self._runner = runner
        self._audit_logger = audit_logger

    @classmethod
    def build_default(cls, policies: list[ScriptPolicy]) -> SkillScriptService:
        """Build service with default dependencies and configured skills root."""
        # 解析skill的地址，没有就是默认.riton/skills
        skills_root = Path(".riton/skills")
        try:
            from config.infra_config import infra_config  # type: ignore

            configured_path = getattr(infra_config, "skill_path", None)
            if configured_path:
                skills_root = Path(configured_path)
        except Exception:
            pass

        return cls(
            path_resolver=PathResolver(skills_root=skills_root),
            policy_engine=PolicyEngine(policies=policies),
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
        interpreter = str(context.get("interpreter", "python"))
        timeout_seconds, timeout_error = self._resolve_requested_timeout(context)
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
                script=script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="invalid_timeout",
            )
            return denied_result

        # Step 1: resolve script path and fail fast when path validation rejects it.
        # 拒绝输入的绝对地址，提供script的地址只能是scripts/xxx.py等，也就是相对当前skill的目录
        # resolved_path是解析后的绝对地址，用这个执行
        allowed_path, resolved_path = self._path_resolver.resolve_script_path(skill_name, script)
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
                script=script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="path_denied",
            )
            return denied_result

        # Step 2: evaluate policy constraints before process execution begins.
        policy_allowed, policy_reason, matched_policy = self._policy_engine.evaluate_with_policy(
            skill_name=skill_name,
            script=script,
            interpreter=interpreter,
            args=args,
        )
        if not policy_allowed:
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail=policy_reason,
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="policy_denied",
            )
            return denied_result

        # Step 3: enforce timeout ceiling declared by the matched execution policy.
        if matched_policy is not None and timeout_seconds > matched_policy.max_timeout_seconds:
            denied_result = ScriptExecutionResult(
                run_id=run_id,
                status=ScriptExecutionStatus.DENIED,
                exit_code=None,
                stdout_tail="",
                stderr_tail=(
                    "Requested timeout_seconds exceeds policy max_timeout_seconds "
                    f"({timeout_seconds} > {matched_policy.max_timeout_seconds})"
                ),
            )
            self._audit_run(
                run_id=run_id,
                skill_name=skill_name,
                script=script,
                status=denied_result.status,
                exit_code=denied_result.exit_code,
                reason="timeout_exceeds_policy",
            )
            return denied_result

        # Step 4: build deterministic process argv and execute via runner.
        serialized_args = json.dumps(args, separators=(",", ":"), sort_keys=True)
        argv = [interpreter, str(resolved_path), serialized_args]
        runner_result = self._runner.run(argv=argv, timeout_seconds=timeout_seconds)

        # Step 5: map runner outcome to execution lifecycle status semantics.
        if runner_result.timed_out:
            status = ScriptExecutionStatus.TIMED_OUT
        elif runner_result.exit_code == 0:
            status = ScriptExecutionStatus.COMPLETED
        else:
            status = ScriptExecutionStatus.FAILED

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
            script=script,
            status=result.status,
            exit_code=result.exit_code,
            reason="completed",
        )
        return result

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
