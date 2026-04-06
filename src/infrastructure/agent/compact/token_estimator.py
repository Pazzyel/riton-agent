from collections.abc import Sequence

from langchain_core.messages import AnyMessage


class MessageTokenEstimator:
    """消息 token 估算器。"""

    def __init__(self, context_window: int = 128000, compact_threshold_ratio: float = 0.9) -> None:
        """初始化上下文窗口和压缩阈值。"""
        self.context_window: int = context_window
        self.compact_threshold_ratio: float = compact_threshold_ratio

    def estimate_messages_tokens(self, messages: Sequence[AnyMessage]) -> int:
        """估算消息总 token 数。"""
        total: int = 0
        message: AnyMessage
        for message in messages:
            total += self._estimate_text_tokens(str(message.content))
        return total

    def should_compact(self, token_count: int) -> bool:
        """判断是否达到压缩阈值。"""
        threshold: int = int(self.context_window * self.compact_threshold_ratio)
        return token_count >= threshold

    def _estimate_text_tokens(self, text: str) -> int:
        """优先使用 tokenizer，失败时退化为字符近似估算。"""
        normalized_text: str = text.strip()
        if normalized_text == "":
            return 0
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(normalized_text))
        except Exception:
            return max(1, len(normalized_text) // 2)
