import sys
import asyncio
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def _ensure_src_path() -> None:
    """确保测试可导入 src 下模块。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()


def test_compact_preserves_latest_user_and_assistant_messages() -> None:
    """压缩后应保留最新用户与助手消息。"""
    from infrastructure.agent.compact.message_compact_service import MessageCompactService

    service: MessageCompactService = MessageCompactService(
        model=_FakeSummaryModel(),
        prompt_loader=_PromptLoaderRecorder().load,
    )
    messages: list = [
        HumanMessage(content="旧问题1"),
        AIMessage(content="旧回答1"),
        HumanMessage(content="最新问题"),
        AIMessage(content="最新回答"),
        ToolMessage(content="很长的工具结果" * 50, tool_call_id="tool1", name="shop_comment_rag"),
    ]

    compacted: list = asyncio.run(service.compact_messages(messages, current_token_count=200000))

    assert any(str(item.content) == "最新问题" for item in compacted)
    assert any(str(item.content) == "最新回答" for item in compacted)


def test_compact_replaces_old_messages_with_summary_message() -> None:
    """压缩后应生成固定模板的摘要消息。"""
    from infrastructure.agent.compact.message_compact_service import MessageCompactService

    service: MessageCompactService = MessageCompactService(
        model=_FakeSummaryModel(),
        prompt_loader=_PromptLoaderRecorder().load,
    )
    messages: list = [
        HumanMessage(content="旧问题1"),
        AIMessage(content="旧回答1"),
        ToolMessage(content="很长的工具结果" * 50, tool_call_id="tool1", name="shop_comment_rag"),
        HumanMessage(content="最新问题"),
        AIMessage(content="最新回答"),
    ]

    compacted: list = asyncio.run(service.compact_messages(messages, current_token_count=200000))

    assert any(item.type == "ai" and "会话摘要" in str(item.content) for item in compacted)


def test_compact_service_loads_summary_prompt_without_short_memory() -> None:
    """总结 prompt 加载时应关闭 short memory 占位符。"""
    from infrastructure.agent.compact.message_compact_service import MessageCompactService

    recorder: _PromptLoaderRecorder = _PromptLoaderRecorder()
    service: MessageCompactService = MessageCompactService(
        model=_FakeSummaryModel(),
        prompt_loader=recorder.load,
    )
    messages: list = [
        HumanMessage(content="旧问题1"),
        AIMessage(content="旧回答1"),
        HumanMessage(content="最新问题"),
        AIMessage(content="最新回答"),
        AIMessage(content="更多旧内容"),
    ]

    asyncio.run(service.compact_messages(messages, 200000))

    assert recorder.calls == [("agent_compact_summary", False)]


def test_compact_service_returns_llm_generated_summary_message() -> None:
    """压缩结果应返回 LLM 生成的摘要消息。"""
    from infrastructure.agent.compact.message_compact_service import MessageCompactService

    service: MessageCompactService = MessageCompactService(
        model=_FakeSummaryModel(),
        prompt_loader=_PromptLoaderRecorder().load,
    )
    messages: list = [
        HumanMessage(content="旧问题1"),
        AIMessage(content="旧回答1"),
        ToolMessage(content="很长的工具结果" * 20, tool_call_id="tool1", name="shop_comment_rag"),
        HumanMessage(content="最新问题"),
        AIMessage(content="最新回答"),
    ]

    compacted: list = asyncio.run(service.compact_messages(messages, 200000))

    assert compacted[0].type == "ai"
    assert "会话摘要" in str(compacted[0].content)


class _PromptLoaderRecorder:
    """记录 prompt_loader 调用参数。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    async def load(self, node_name: str, with_short_memory: bool = True):
        self.calls.append((node_name, with_short_memory))
        return _FakeSummaryPrompt()


class _FakeSummaryPrompt:
    """测试用总结 prompt。"""

    def format_messages(self, **kwargs: object) -> list[tuple[str, str]]:
        history_text: str = str(kwargs.get("history_text", ""))
        return [("user", f"summary::{history_text}")]


class _FakeSummaryModel:
    """测试用总结模型。"""

    async def ainvoke(self, messages: list[tuple[str, str]]) -> AIMessage:
        _ = messages
        return AIMessage(content="会话摘要\n1. 用户目标\n- 测试")
