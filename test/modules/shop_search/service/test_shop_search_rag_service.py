import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from langchain_core.documents import Document


def _ensure_src_path() -> None:
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()

from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService


class DummyHybridRetrieverService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def retrieve(
        self,
        query: str,
        top_k: int,
        filters: list[dict] | None = None,
    ) -> list[Document]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "filters": filters,
            }
        )
        now: datetime = datetime.now()
        old_time: datetime = now - timedelta(days=500)
        return [
            Document(page_content="生日布置很用心", metadata={"create_time": now.isoformat()}),
            Document(page_content="很久以前的评论", metadata={"create_time": old_time.isoformat()}),
        ]


def test_retrieve_comments_uses_hybrid_rerank_and_filters_old_records() -> None:
    retriever = DummyHybridRetrieverService()
    service = ShopSearchRagService(retriever)

    comments = asyncio.run(service.retrieve_comments(1001, "生日"))

    assert comments == ["生日布置很用心"]
    assert retriever.calls[0]["filters"] == [{"term": {"metadata.shop_id.keyword": "1001"}}]
    assert retriever.calls[0]["top_k"] == 8


class DummyAwareTimeRetrieverService:
    async def retrieve(
        self,
        query: str,
        top_k: int,
        filters: list[dict] | None = None,
    ) -> list[Document]:
        _ = query
        _ = top_k
        _ = filters
        aware_now: datetime = datetime.now(timezone.utc)
        return [
            Document(page_content="带时区的新评论", metadata={"create_time": aware_now.isoformat()}),
        ]


def test_retrieve_comments_accepts_timezone_aware_create_time() -> None:
    service = ShopSearchRagService(DummyAwareTimeRetrieverService())

    comments = asyncio.run(service.retrieve_comments(1001, "生日"))

    assert comments == ["带时区的新评论"]
