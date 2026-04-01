from pathlib import Path
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

from infrastructure.sandbox.models import ScriptPolicy
from infrastructure.sandbox.policy_engine import PolicyEngine


def _build_policy() -> ScriptPolicy:
    """Create a baseline policy used by policy engine tests."""
    return ScriptPolicy(
        allowed_skills=["skill-a"],
        max_timeout_seconds=30,
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python",
        required_args=["name"],
        allowed_args=["name", "count"],
        arg_types={"name": str, "count": int},
    )


def test_policy_engine_accepts_valid_input() -> None:
    """Policy engine should allow valid invocation input."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python",
        args={"name": "alex", "count": 2},
    )

    assert is_valid is True
    assert reason == "ok"


def test_policy_engine_rejects_when_no_policy_matches() -> None:
    """Policy engine should deny calls that do not match skill/script/interpreter."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-b",
        script="scripts/other.py",
        interpreter="bash",
        args={"name": "alex"},
    )

    assert is_valid is False
    assert reason == "No policy matched skill/script/interpreter"


def test_policy_engine_rejects_missing_required_args() -> None:
    """Policy engine should deny invocations with missing required arguments."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python",
        args={},
    )

    assert is_valid is False
    assert reason == "Missing required argument: name"


def test_policy_engine_rejects_unknown_args() -> None:
    """Policy engine should deny unknown arguments not in allowed args."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python",
        args={"name": "alex", "unexpected": True},
    )

    assert is_valid is False
    assert reason == "Unknown argument: unexpected"


def test_policy_engine_rejects_type_mismatch() -> None:
    """Policy engine should deny arguments with invalid runtime types."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python",
        args={"name": "alex", "count": "two"},
    )

    assert is_valid is False
    assert reason == "Invalid type for argument count: expected int"
