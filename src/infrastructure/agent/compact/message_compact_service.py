from langchain_core.messages import AIMessage, AnyMessage


class MessageCompactService:
    """消息压缩服务。"""

    def compact_messages(self, messages: list[AnyMessage], current_token_count: int) -> list[AnyMessage]:
        """
        压缩消息列表。

        传入次函数的消息，应该自行先进行token阈值检测
        """
        _ = current_token_count
        if len(messages) <= 4:
            return messages

        # 最近3条消息不压缩
        recent_messages: list[AnyMessage] = messages[-4:]
        # 只压缩旧的消息
        old_messages: list[AnyMessage] = messages[:-4]
        summary_message: AIMessage = AIMessage(content=self._build_summary(old_messages))
        return [summary_message, *recent_messages] # 总结的在前面，保留的在后面

    def _build_summary(self, messages: list[AnyMessage]) -> str:
        """
        按固定模板构建摘要。
        """

        # TODO 使用大模型总结
        high_value_lines: list[str] = []
        item: AnyMessage
        for item in messages:
            content_text: str = str(item.content)
            tool_name: str = str(getattr(item, "name", "") or "")
            if "shop_comment_rag" in tool_name:
                high_value_lines.append(f"已查询结果: {content_text[:200]}")
            elif item.type == "human":
                high_value_lines.append(f"用户目标: {content_text[:120]}")
            elif item.type == "ai":
                high_value_lines.append(f"已承诺方案: {content_text[:120]}")

        return "\n".join(
            [
                "之前的会话摘要",
                "1. 用户目标",
                *high_value_lines[:6],
                "8. 下一步动作",
                "继续基于最新问题回答用户。",
                "9. 禁忌事项/不要再问的内容",
                "不要重复追问已确认信息。",
            ]
        )
