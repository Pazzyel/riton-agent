import sys
from pathlib import Path

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


def test_estimate_message_tokens_returns_positive_value() -> None:
    """消息 token 估算结果应为正数。"""
    from infrastructure.agent.compact.token_estimator import MessageTokenEstimator

    estimator: MessageTokenEstimator = MessageTokenEstimator()
    messages: list = [
        HumanMessage(content="我想找适合生日聚餐的火锅店"),
        AIMessage(content="我先帮你看看静安区附近的高评分候选"),
    ]

    token_count: int = estimator.estimate_messages_tokens(messages)

    assert token_count > 0


def test_should_compact_when_reaching_ninety_percent_window() -> None:
    """达到 128k 窗口的 0.9 时应触发压缩。"""
    from infrastructure.agent.compact.token_estimator import MessageTokenEstimator

    estimator: MessageTokenEstimator = MessageTokenEstimator(
        context_window=128000,
        compact_threshold_ratio=0.9,
    )

    assert estimator.should_compact(115200) is True
    assert estimator.should_compact(115199) is False
