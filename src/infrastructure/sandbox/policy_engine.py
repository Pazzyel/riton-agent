"""Policy evaluation logic for sandbox script execution."""

from infrastructure.sandbox.models import ScriptPolicy


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
        # Step 1: resolve the policy entry for the requested execution identity.
        matching_policy = self._find_matching_policy(
            skill_name=skill_name,
            script=script,
            interpreter=interpreter,
        )
        if matching_policy is None:
            return False, "No policy matched skill/script/interpreter", None

        # Step 2: enforce argument presence constraints from the matched policy.
        required_args_ok, required_args_reason = self._validate_required_args(
            policy=matching_policy,
            args=args,
        )
        if not required_args_ok:
            return False, required_args_reason, matching_policy

        # Step 3: reject invocation keys that the policy does not recognize.
        unknown_args_ok, unknown_args_reason = self._validate_unknown_args(
            policy=matching_policy,
            args=args,
        )
        if not unknown_args_ok:
            return False, unknown_args_reason, matching_policy

        # Step 4: validate runtime values against declared argument types.
        arg_types_ok, arg_types_reason = self._validate_arg_types(
            policy=matching_policy,
            args=args,
        )
        if not arg_types_ok:
            return False, arg_types_reason, matching_policy

        return True, "ok", matching_policy

    def _find_matching_policy(
        self,
        skill_name: str,
        script: str,
        interpreter: str,
    ) -> ScriptPolicy | None:
        """Return the first policy that matches skill, script, and interpreter."""
        for policy in self._policies:
            # Check each identifier explicitly so mismatch reasons are deterministic.
            if policy.skill_name is not None and policy.skill_name != skill_name:
                continue
            if policy.script is not None and policy.script != script:
                continue
            if policy.interpreter is not None and policy.interpreter != interpreter:
                continue
            if policy.allowed_skills and skill_name not in policy.allowed_skills:
                continue
            return policy

        return None

    def _validate_required_args(
        self,
        policy: ScriptPolicy,
        args: dict[str, object],
    ) -> tuple[bool, str]:
        """Ensure all required policy arguments are provided."""
        for required_arg in policy.required_args:
            if required_arg not in args:
                return False, f"Missing required argument: {required_arg}"

        return True, "ok"

    def _validate_unknown_args(
        self,
        policy: ScriptPolicy,
        args: dict[str, object],
    ) -> tuple[bool, str]:
        """Ensure invocation does not include arguments outside allowed set."""
        if not policy.allowed_args:
            return True, "ok"

        for arg_name in args:
            if arg_name not in policy.allowed_args:
                return False, f"Unknown argument: {arg_name}"

        return True, "ok"

    def _validate_arg_types(
        self,
        policy: ScriptPolicy,
        args: dict[str, object],
    ) -> tuple[bool, str]:
        """Ensure invocation argument values match declared argument types."""
        # Validate only supplied args that have a declared type contract.
        for arg_name, expected_type in policy.arg_types.items():
            if arg_name not in args:
                continue
            if not isinstance(args[arg_name], expected_type):
                return (
                    False,
                    f"Invalid type for argument {arg_name}: expected {expected_type.__name__}",
                )

        return True, "ok"
