from typing import Any

from langchain_core.messages import RemoveMessage, AnyMessage
from langgraph.types import Command

from infrastructure.agent.compact.message_compact_service import MessageCompactService
from infrastructure.agent.compact.token_estimator import MessageTokenEstimator


class CompactNodeFactory:
    """压缩节点工厂。"""

    def __init__(
        self,
        token_estimator: MessageTokenEstimator,
        compact_service: MessageCompactService,
        message_key: str = "messages",
    ) -> None:
        """初始化压缩节点工厂。"""
        self.token_estimator: MessageTokenEstimator = token_estimator
        self.compact_service: MessageCompactService = compact_service
        self.message_key: str = message_key

    def build_node(self, goto: str):
        """构建压缩节点函数。"""

        def node(state: dict[str, Any]) -> Command:
            messages: Any = state.get(self.message_key, [])
            if not isinstance(messages, list) or len(messages) == 0:
                return Command(update={}, goto=goto)

            token_count: int = self.token_estimator.estimate_messages_tokens(messages)
            if not self.token_estimator.should_compact(token_count):
                return Command(update={}, goto=goto)

            compacted_messages: list[Any] = self.compact_service.compact_messages(messages, token_count)

            # 没有达到阈值，不总结
            if compacted_messages == messages:
                return Command(update={}, goto=goto)

            # 发生总结，替换
            return Command(
                update={self.message_key: self._replace_all_messages(messages, compacted_messages)},
                goto=goto,
            )

        return node

    def _replace_all_messages(self, current_messages: list[AnyMessage], next_messages: list[AnyMessage]) -> list[AnyMessage]:
        """生成用于替换完整消息快照的更新列表。"""
        # 移除当前的所有消息
        removals: list[RemoveMessage] = [RemoveMessage(id=message.id) for message in current_messages]
        # 添加新的压缩后消息
        return [*removals, *next_messages]
