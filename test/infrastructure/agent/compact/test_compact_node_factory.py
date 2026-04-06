import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage


def _ensure_src_path() -> None:
    """确保测试可导入 src 下模块。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()


def test_factory_builds_passthrough_node_when_below_threshold() -> None:
    """未达到阈值时压缩节点应直接透传。"""
    from infrastructure.agent.compact.compact_node_factory import CompactNodeFactory

    factory: CompactNodeFactory = CompactNodeFactory(
        token_estimator=_FakeEstimator(token_count=10, should_compact_flag=False),
        compact_service=_FakeCompactService(),
    )
    node = factory.build_node("next_node")
    state: dict[str, Any] = {"messages": [HumanMessage(content="hello")]}

    command = node(state)

    assert command.goto == "next_node"
    assert command.update == {}


def test_factory_builds_replace_all_update_when_threshold_reached() -> None:
    """达到阈值时压缩节点应返回全量替换更新。"""
    from infrastructure.agent.compact.compact_node_factory import CompactNodeFactory

    factory: CompactNodeFactory = CompactNodeFactory(
        token_estimator=_FakeEstimator(token_count=200000, should_compact_flag=True),
        compact_service=_FakeCompactService(),
    )
    node = factory.build_node("next_node")
    state: dict[str, Any] = {
        "messages": [
            HumanMessage(content="hello"),
            AIMessage(content="world"),
        ]
    }

    command = node(state)

    assert command.goto == "next_node"
    assert len(command.update["messages"]) == 3


class _FakeEstimator:
    """测试用估算器。"""

    def __init__(self, token_count: int, should_compact_flag: bool) -> None:
        self.token_count: int = token_count
        self.should_compact_flag: bool = should_compact_flag

    def estimate_messages_tokens(self, messages: list[Any]) -> int:
        _ = messages
        return self.token_count

    def should_compact(self, token_count: int) -> bool:
        _ = token_count
        return self.should_compact_flag


class _FakeCompactService:
    """测试用压缩服务。"""

    def compact_messages(self, messages: list[Any], current_token_count: int) -> list[Any]:
        _ = messages
        _ = current_token_count
        return [AIMessage(content="compacted")]
