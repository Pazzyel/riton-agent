from datetime import datetime, timedelta
from typing import Protocol

from langchain_core.documents import Document


class CommentRetrieverProtocol(Protocol):
    async def retrieve(
        self,
        query: str,
        top_k: int,
        filters: list[dict] | None = None,
    ) -> list[Document]:
        ...


class ShopSearchRagService:
    """商铺推荐评论检索服务。"""

    def __init__(self, comment_retriever: CommentRetrieverProtocol) -> None:
        self.comment_retriever: CommentRetrieverProtocol = comment_retriever

    async def retrieve_comments(
        self,
        shop_id: int,
        keyword: str,
        top_k: int = 8,
    ) -> list[str]:
        documents: list[Document] = await self.comment_retriever.retrieve(
            query=keyword,
            top_k=top_k,
            filters=[{"term": {"metadata.shop_id.keyword": str(shop_id)}}],
        )
        now: datetime = datetime.now()
        min_time: datetime = now - timedelta(days=365)

        comments: list[str] = []
        document: Document
        for document in documents:
            create_time_text: str = str(document.metadata.get("create_time", ""))
            content_text: str = str(document.page_content).strip()
            if content_text == "":
                continue

            parsed_time: datetime | None = self._safe_parse_time(create_time_text)
            if parsed_time is None:
                continue
            if parsed_time >= min_time:
                comments.append(content_text)

        return comments[:top_k]

    def _safe_parse_time(self, value: str) -> datetime | None:
        """安全解析 ISO 时间文本。"""
        if value.strip() == "":
            return None
        try:
            parsed_time: datetime = datetime.fromisoformat(value)
            if parsed_time.tzinfo is not None:
                return parsed_time.astimezone().replace(tzinfo=None)
            return parsed_time
        except ValueError:
            return None
