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
from infrastructure.sandbox.policy_engine import (
    PolicyEngine,
    build_policy_key,
    infer_interpreter_for_script,
    scan_script_policies,
)


def _build_policy() -> ScriptPolicy:
    """Create a baseline policy used by policy engine tests."""
    return ScriptPolicy(
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python3",
    )


def test_policy_engine_accepts_valid_input() -> None:
    """Policy engine should allow valid invocation input."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-a",
        script="scripts/hello.py",
        interpreter="python3",
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


def test_policy_engine_accepts_backslash_script_path() -> None:
    """Policy engine should normalize incoming script separators before matching."""
    engine = PolicyEngine([_build_policy()])

    is_valid, reason = engine.evaluate(
        skill_name="skill-a",
        script=r"scripts\hello.py",
        interpreter="python3",
        args={},
    )

    assert is_valid is True
    assert reason == "ok"


def test_infer_interpreter_for_script_supports_known_suffixes() -> None:
    """Interpreter inference should map supported script suffixes."""
    assert infer_interpreter_for_script("scripts/run.py") == "python3"
    assert infer_interpreter_for_script("scripts/run.js") == "node"
    assert infer_interpreter_for_script("scripts/run.ts") == "node"


def test_infer_interpreter_for_script_returns_none_for_unknown_suffix() -> None:
    """Interpreter inference should return None for unsupported suffixes."""
    assert infer_interpreter_for_script("scripts/run.sh") is None
    assert infer_interpreter_for_script("scripts/run") is None


def test_build_policy_key_normalizes_path_separators() -> None:
    """Policy key builder should normalize slash and backslash separators."""
    assert build_policy_key("skill-a", r"scripts\\nested\\run.py") == "skill-a/scripts/nested/run.py"


def test_scan_script_policies_collects_supported_script_entries(tmp_path: Path) -> None:
    """Policy scanning should include supported suffixes and skip unknown files."""
    skill_dir = tmp_path / "skill-a" / "scripts" / "nested"
    skill_dir.mkdir(parents=True)
    (skill_dir / "run.py").write_text("print('ok')", encoding="utf-8")
    (skill_dir / "worker.ts").write_text("console.log('ok')", encoding="utf-8")
    (skill_dir / "README.md").write_text("ignored", encoding="utf-8")

    policies = scan_script_policies(tmp_path)

    assert set(policies.keys()) == {
        "skill-a/scripts/nested/run.py",
        "skill-a/scripts/nested/worker.ts",
    }
    assert policies["skill-a/scripts/nested/run.py"] == ScriptPolicy(
        skill_name="skill-a",
        script="scripts/nested/run.py",
        interpreter="python3",
    )
    assert policies["skill-a/scripts/nested/worker.ts"] == ScriptPolicy(
        skill_name="skill-a",
        script="scripts/nested/worker.ts",
        interpreter="node",
    )
