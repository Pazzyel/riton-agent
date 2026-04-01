"""Minimal runnable example for sandboxed skill script execution."""

import json
from pathlib import Path

from infrastructure.sandbox.models import ScriptPolicy
from infrastructure.sandbox.skill_script_service import SkillScriptService

# 实际过程中，需要扫描对应目录下的skills，获取所有可用的skill
def _build_demo_policy() -> ScriptPolicy:
    """Create one demo policy allowing the echo script invocation."""
    return ScriptPolicy(
        allowed_skills=["demo"],
        max_timeout_seconds=30,
        skill_name="demo",
        script="scripts/echo_args.py",
        interpreter="python",
        required_args=["message"],
        allowed_args=["message", "count"],
        arg_types={"message": str, "count": int},
    )


def run_example() -> dict[str, object]:
    """Run demo sandbox execution and return a normalized dictionary."""
    # Setup and wiring: build one demo policy and create default sandbox service.
    script_file = Path(__file__).resolve()
    project_root = script_file.parents[3]
    policy = _build_demo_policy()
    service = SkillScriptService.build_default([policy])
    # Keep the example runnable from any cwd by pinning skills root to repository path.
    service._path_resolver._skills_root = (project_root / ".riton" / "skills").resolve()

    # Execution call: run the demo skill script with simple typed arguments.
    result = service.execute_skill_script(
        skill_name="demo",
        script="scripts/echo_args.py",
        args={"message": "hello from sandbox", "count": 2},
        context={"interpreter": "python", "timeout_seconds": 10},
    )

    # Result normalization: expose the required response keys as plain JSON-friendly values.
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
