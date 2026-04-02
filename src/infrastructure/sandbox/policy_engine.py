"""Policy helpers and matching for sandbox script execution."""

from __future__ import annotations

from pathlib import Path

from infrastructure.sandbox.models import ScriptPolicy


def infer_interpreter_for_script(script_path: str) -> str | None:
    """Infer interpreter name from the script file suffix."""
    suffix = Path(script_path).suffix.lower()
    if suffix == ".py":
        return "python3"
    if suffix in {".js", ".ts"}:
        return "node"
    return None


def build_policy_key(skill_name: str, script: str) -> str:
    """Build a stable policy key from skill and script path."""
    normalized_script = "/".join(part for part in script.replace("\\", "/").split("/") if part)
    return f"{skill_name}/{normalized_script}"


def scan_script_policies(skills_root: Path) -> dict[str, ScriptPolicy]:
    """Scan skill script files and return inferred policies keyed by skill/script."""
    policies: dict[str, ScriptPolicy] = {}

    # Step 1: walk each skill's scripts directory and gather candidate files.
    for skill_dir in sorted(skills_root.glob("*")):
        if not skill_dir.is_dir():
            continue
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.is_dir():
            continue

        # Step 2: infer interpreter by suffix and skip unsupported file types.
        for script_file in sorted(scripts_dir.rglob("*")):
            if not script_file.is_file():
                continue
            interpreter = infer_interpreter_for_script(script_file.name)
            if interpreter is None:
                continue

            # Step 3: build normalized script path and map it to a ScriptPolicy.
            relative_script = script_file.relative_to(skill_dir).as_posix()
            key = build_policy_key(skill_dir.name, relative_script)
            policies[key] = ScriptPolicy(
                skill_name=skill_dir.name,
                script=relative_script,
                interpreter=interpreter,
            )

    return policies


class PolicyEngine:
    """Validate script execution requests against configured policies."""

    def __init__(self, policies: list[ScriptPolicy]) -> None:
        """Initialize the policy engine with script policies."""
        self._policies = policies

    def evaluate(
        self,
        skill_name: str,
        script: str,
        interpreter: str,
        args: dict[str, object],
    ) -> tuple[bool, str]:
        """Evaluate whether a script invocation is allowed by policy."""
        is_allowed, reason, _ = self.evaluate_with_policy(
            skill_name=skill_name,
            script=script,
            interpreter=interpreter,
            args=args,
        )
        return is_allowed, reason

    def evaluate_with_policy(
        self,
        skill_name: str,
        script: str,
        interpreter: str,
        args: dict[str, object],
    ) -> tuple[bool, str, ScriptPolicy | None]:
        """Evaluate policy and include the matched policy when available."""
        del args
        matching_policy = self._find_matching_policy(skill_name, script, interpreter)
        if matching_policy is None:
            return False, "No policy matched skill/script/interpreter", None
        return True, "ok", matching_policy

    def _find_matching_policy(
        self,
        skill_name: str,
        script: str,
        interpreter: str,
    ) -> ScriptPolicy | None:
        """Return the first policy that matches skill, script, and interpreter."""
        requested_key = build_policy_key(skill_name, script)
        for policy in self._policies:
            policy_key = build_policy_key(policy.skill_name, policy.script)
            if policy_key != requested_key:
                continue
            if policy.interpreter != interpreter:
                continue
            return policy
        return None
