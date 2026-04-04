from datetime import datetime, timedelta
from typing import Any, Protocol


class BlogRetrieverProtocol(Protocol):
    """评论向量检索协议。"""

    async def retrieve_by_shop(
        self,
        shop_id: int,
        keyword: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """按店铺和关键词检索评论。"""


class ShopSearchRagService:
    """商铺推荐评论检索服务。"""

    def __init__(self, blog_retriever: BlogRetrieverProtocol) -> None:
        """初始化评论检索服务。"""
        self.blog_retriever: BlogRetrieverProtocol = blog_retriever

    async def retrieve_comments(
        self,
        shop_id: int,
        keyword: str,
        top_k: int = 8,
    ) -> list[str]:
        """检索并过滤一年内评论文本。"""
        rows: list[dict[str, Any]] = await self.blog_retriever.retrieve_by_shop(
            shop_id,
            keyword,
            top_k,
        )
        now: datetime = datetime.now()
        min_time: datetime = now - timedelta(days=365)

        # 关键步骤：仅保留 create_time 在一年内的评论。
        comments: list[str] = []
        row: dict[str, Any]
        for row in rows:
            create_time_text: str = str(row.get("create_time", ""))
            content_text: str = str(row.get("content", "")).strip()
            if content_text == "":
                continue

            parsed_time: datetime | None = self._safe_parse_time(create_time_text)
            if parsed_time is None:
                continue
            if parsed_time >= min_time:
                comments.append(content_text)

        return comments

    def _safe_parse_time(self, value: str) -> datetime | None:
        """安全解析 ISO 时间文本。"""
        if value.strip() == "":
            return None
        try:
            parsed_time: datetime = datetime.fromisoformat(value)
            return parsed_time
        except ValueError:
            return None
