import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from langchain_core.documents import Document


def _ensure_src_path() -> None:
    """确保测试可以导入 src 下模块。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()

from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService


class DummyBlogVectorService:
    """用于测试的评论向量服务。"""

    def get_retriever(
        self,
        search_type: str = "similarity_score_threshold",
        search_kwargs: dict | None = None,
    ) -> object:
        """返回带固定文档的 retriever。"""
        assert search_type == "similarity_score_threshold"
        assert search_kwargs is not None
        assert search_kwargs["k"] == 8
        assert search_kwargs["filter"] == [{"term": {"metadata.shop_id.keyword": "1001"}}]
        return _DummyRetriever()


class _DummyRetriever:
    """用于测试的 retriever。"""

    async def ainvoke(self, keyword: str) -> list[Document]:
        """返回包含新旧评论的混合文档。"""
        _ = keyword
        now: datetime = datetime.now()
        old_time: datetime = now - timedelta(days=500)
        return [
            Document(page_content="生日布置很用心", metadata={"create_time": now.isoformat()}),
            Document(page_content="很久以前的评论", metadata={"create_time": old_time.isoformat()}),
        ]


def test_retrieve_comments_filters_old_records() -> None:
    """应仅保留一年内评论。"""
    service: ShopSearchRagService = ShopSearchRagService(DummyBlogVectorService())
    comments: list[str] = asyncio.run(service.retrieve_comments(1001, "生日"))
    assert comments == ["生日布置很用心"]
