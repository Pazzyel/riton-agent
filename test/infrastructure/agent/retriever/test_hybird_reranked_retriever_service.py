import asyncio
import sys
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

from infrastructure.agent.retriever.hybird_reranked_retriever_service import HybirdRerankedRetrieverService


class _FakeHybridRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.calls: list[dict] = []

    async def retrieve(self, **kwargs: object) -> list[Document]:
        self.calls.append(kwargs)
        return self.documents


class _FakeReranker:
    def __init__(self, should_raise: bool = False) -> None:
        self.should_raise = should_raise
        self.calls: list[tuple[str, list[Document]]] = []

    async def rerank(self, query: str, documents: list[Document]) -> list[Document]:
        self.calls.append((query, documents))
        if self.should_raise:
            raise RuntimeError("ollama unavailable")
        return list(reversed(documents))


def test_hybird_service_reranks_after_hybrid_retrieve() -> None:
    documents = [
        Document(page_content="A", metadata={"id": "1"}),
        Document(page_content="B", metadata={"id": "2"}),
    ]
    hybrid = _FakeHybridRetriever(documents)
    reranker = _FakeReranker()
    service = HybirdRerankedRetrieverService(hybrid, reranker)

    result = asyncio.run(
        service.retrieve(
            query="生日",
            top_k=8,
            filters=[{"term": {"metadata.shop_id.keyword": "1001"}}],
        )
    )

    assert result[0].metadata["id"] == "2"
    assert hybrid.calls[0]["top_k"] == 8
    assert hybrid.calls[0]["filters"] == [{"term": {"metadata.shop_id.keyword": "1001"}}]
    assert reranker.calls[0][0] == "生日"


def test_hybird_service_falls_back_when_rerank_fails() -> None:
    documents = [Document(page_content="A", metadata={"id": "1"})]
    hybrid = _FakeHybridRetriever(documents)
    reranker = _FakeReranker(should_raise=True)
    service = HybirdRerankedRetrieverService(hybrid, reranker)

    result = asyncio.run(
        service.retrieve(
            query="生日",
            top_k=8,
            filters=[{"term": {"metadata.shop_id.keyword": "1001"}}],
        )
    )

    assert result == documents


def test_hybird_service_passes_none_filters_through_unchanged() -> None:
    documents = [Document(page_content="A", metadata={"id": "1"})]
    hybrid = _FakeHybridRetriever(documents)
    reranker = _FakeReranker()
    service = HybirdRerankedRetrieverService(hybrid, reranker)

    asyncio.run(
        service.retrieve(
            query="生日",
            top_k=8,
            filters=None,
        )
    )

    assert hybrid.calls[0]["filters"] is None
