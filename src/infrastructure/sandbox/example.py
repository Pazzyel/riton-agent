"""Minimal runnable example for sandboxed skill script execution."""

import json
from pathlib import Path

from infrastructure.sandbox.audit_logger import SandboxAuditLogger
from infrastructure.sandbox.local_runner import LocalRunner
from infrastructure.sandbox.path_resolver import PathResolver
from infrastructure.sandbox.policy_engine import scan_script_policies
from infrastructure.sandbox.skill_script_service import SkillScriptService


def _build_example_service(skills_root: Path) -> SkillScriptService:
    """Construct a service using auto-scanned policies under the given skills root."""
    policy_map = scan_script_policies(skills_root)
    return SkillScriptService(
        path_resolver=PathResolver(skills_root=skills_root),
        allowed_skills={"demo"},
        policy_map=policy_map,
        runner=LocalRunner(),
        audit_logger=SandboxAuditLogger(),
    )


def run_example() -> dict[str, object]:
    """Run demo sandbox execution and return a normalized dictionary."""
    script_file = Path(__file__).resolve()
    project_root = script_file.parents[3]
    service = _build_example_service((project_root / ".riton" / "skills").resolve())

    result = service.execute_skill_script(
        skill_name="demo",
        script="scripts/echo_args.py",
        args={"message": "hello from sandbox", "count": 2},
        context={"interpreter": "python", "timeout_seconds": 10},
    )

    return {
        "run_id": result.run_id,
        "status": result.status.value,
        "exit_code": result.exit_code,
        "stdout_tail": result.stdout_tail,
        "stderr_tail": result.stderr_tail,
        "output_files": result.output_files,
    }


def main() -> None:
    """Execute the example and print JSON output for manual smoke runs."""
    print(json.dumps(run_example(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
