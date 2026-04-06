import sys
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

    service: MessageCompactService = MessageCompactService()
    messages: list = [
        HumanMessage(content="旧问题1"),
        AIMessage(content="旧回答1"),
        HumanMessage(content="最新问题"),
        AIMessage(content="最新回答"),
        ToolMessage(content="很长的工具结果" * 50, tool_call_id="tool1", name="shop_comment_rag"),
    ]

    compacted: list = service.compact_messages(messages, current_token_count=200000)

    assert any(str(item.content) == "最新问题" for item in compacted)
    assert any(str(item.content) == "最新回答" for item in compacted)


def test_compact_replaces_old_messages_with_summary_message() -> None:
    """压缩后应生成固定模板的摘要消息。"""
    from infrastructure.agent.compact.message_compact_service import MessageCompactService

    service: MessageCompactService = MessageCompactService()
    messages: list = [
        HumanMessage(content="旧问题1"),
        AIMessage(content="旧回答1"),
        ToolMessage(content="很长的工具结果" * 50, tool_call_id="tool1", name="shop_comment_rag"),
        HumanMessage(content="最新问题"),
        AIMessage(content="最新回答"),
    ]

    compacted: list = service.compact_messages(messages, current_token_count=200000)

    assert any(item.type == "ai" and "会话摘要" in str(item.content) for item in compacted)
