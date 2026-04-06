from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage


class MessageCompactService:
    """消息压缩服务。"""

    def __init__(self, model: Any, prompt_loader: Callable[..., Awaitable[Any]]) -> None:
        """初始化消息压缩服务。"""
        self.model: Any = model
        self.prompt_loader: Callable[..., Awaitable[Any]] = prompt_loader

    async def compact_messages(self, messages: list[AnyMessage], current_token_count: int) -> list[AnyMessage]:
        """
        压缩消息列表。

        传入此函数的消息，应该自行先进行 token 阈值检测。
        """
        _ = current_token_count
        if len(messages) <= 4:
            return messages

        recent_messages: list[AnyMessage] = messages[-4:]
        old_messages: list[AnyMessage] = messages[:-4]
        summary_text: str = await self._build_summary(old_messages)
        summary_message: AIMessage = AIMessage(content=summary_text)
        return [summary_message, *recent_messages]

    async def _build_summary(self, messages: list[AnyMessage]) -> str:
        """使用 LLM 按固定模板构建摘要。"""
        history_text: str = self._serialize_messages(messages)
        prompt: Any = await self.prompt_loader("agent_compact_summary", with_short_memory=False)
        response: Any = await self.model.ainvoke(
            prompt.format_messages(history_text=history_text)
        )
        return str(response.content).strip()

    def _serialize_messages(self, messages: list[AnyMessage]) -> str:
        """将历史消息序列化为稳定的文本格式。"""
        lines: list[str] = []
        item: AnyMessage
        for item in messages:
            tool_name: str = str(getattr(item, "name", "") or getattr(item, "tool_name", "") or "")
            if tool_name:
                lines.append(f"[{item.type}:{tool_name}] {str(item.content)}")
            else:
                lines.append(f"[{item.type}] {str(item.content)}")
        return "\n".join(lines)
