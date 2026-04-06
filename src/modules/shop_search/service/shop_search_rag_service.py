from datetime import datetime, timedelta

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService


class ShopSearchRagService:
    """商铺推荐评论检索服务。"""

    def __init__(self, blog_vectorize_service: BlogVectorizeService) -> None:
        """初始化评论检索服务。"""
        self.blog_vectorize_service: BlogVectorizeService = blog_vectorize_service

    async def retrieve_comments(
        self,
        shop_id: int,
        keyword: str,
        top_k: int = 8,
    ) -> list[str]:
        """检索并过滤一年内评论文本。"""
        retriever: VectorStoreRetriever = self.blog_vectorize_service.get_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": top_k,
                "score_threshold": 0.0,
                "filter": [{"term": {"metadata.shop_id.keyword": str(shop_id)}}],
            },
        )
        documents: list[Document] = await retriever.ainvoke(keyword)
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
            return parsed_time
        except ValueError:
            return None
