import asyncio
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


def _ensure_src_path() -> None:
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()

from infrastructure.agent.retriever.hybrid_es_rrf_retriever import HybridEsRrfRetriever


class _FakeEmbedding:
    async def aembed_query(self, query: str) -> list[float]:
        assert query == "生日聚餐"
        return [0.12, 0.34, 0.56]


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def search(self, *, index: str, body: dict) -> dict:
        self.calls.append((index, body))
        return {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "text": "包厢适合过生日",
                            "metadata": {"shop_id": "1001", "create_time": "2026-03-01T08:00:00"},
                        }
                    },
                    {
                        "_source": {
                            "text": "服务员会主动帮忙拍照",
                            "metadata": {"shop_id": "1001", "create_time": "2026-03-02T08:00:00"},
                        }
                    },
                ]
            }
        }


class _FakeStore:
    def __init__(self) -> None:
        self.client = _FakeClient()
        self.embedding = _FakeEmbedding()


class _FakeVectorService:
    def __init__(self) -> None:
        self._index_url = "vector/blog"
        self._store = _FakeStore()


def test_hybrid_es_rrf_retriever_builds_weighted_rrf_query() -> None:
    retriever = HybridEsRrfRetriever(_FakeVectorService())

    documents: list[Document] = asyncio.run(
        retriever.retrieve(
            query="生日聚餐",
            top_k=8,
            filters=[{"term": {"metadata.shop_id.keyword": "1001"}}],
        )
    )

    client = retriever._vector_service._store.client
    assert len(documents) == 2
    assert documents[0].page_content == "包厢适合过生日"
    assert documents[0].metadata == {"shop_id": "1001", "create_time": "2026-03-01T08:00:00"}
    assert client.calls[0][0] == "vector/blog"
    assert client.calls[0][1]["size"] == 80
    assert client.calls[0][1]["retriever"]["rrf"]["rank_window_size"] == 80
    assert client.calls[0][1]["retriever"]["rrf"]["rank_constant"] == 60
    assert "boost" not in client.calls[0][1]["retriever"]["rrf"]["retrievers"][0]["standard"]["query"]["match"]["text"]
    assert client.calls[0][1]["retriever"]["rrf"]["retrievers"][0]["standard"]["filter"] == [
        {"term": {"metadata.shop_id.keyword": "1001"}}
    ]
    assert "boost" not in client.calls[0][1]["retriever"]["rrf"]["retrievers"][1]["knn"]
    assert client.calls[0][1]["retriever"]["rrf"]["retrievers"][1]["knn"]["filter"] == [
        {"term": {"metadata.shop_id.keyword": "1001"}}
    ]
    assert "num_candidates" not in client.calls[0][1]["retriever"]["rrf"]["retrievers"][1]["knn"]


def test_hybrid_es_rrf_retriever_is_a_baseretriever() -> None:
    retriever = HybridEsRrfRetriever(_FakeVectorService())

    assert isinstance(retriever, BaseRetriever)


def test_hybrid_es_rrf_retriever_ainvoke_uses_default_topk_and_filters() -> None:
    retriever = HybridEsRrfRetriever(
        _FakeVectorService(),
        default_top_k=3,
        default_filters=[{"term": {"metadata.shop_id.keyword": "2002"}}],
    )

    documents: list[Document] = asyncio.run(retriever.ainvoke("生日聚餐"))

    client = retriever._vector_service._store.client
    assert len(documents) == 2
    assert client.calls[0][1]["size"] == 30
    assert client.calls[0][1]["retriever"]["rrf"]["retrievers"][0]["standard"]["filter"] == [
        {"term": {"metadata.shop_id.keyword": "2002"}}
    ]
    assert client.calls[0][1]["retriever"]["rrf"]["retrievers"][1]["knn"]["filter"] == [
        {"term": {"metadata.shop_id.keyword": "2002"}}
    ]


def test_hybrid_es_rrf_retriever_invoke_uses_default_topk_and_filters() -> None:
    retriever = HybridEsRrfRetriever(
        _FakeVectorService(),
        default_top_k=3,
        default_filters=[{"term": {"metadata.shop_id.keyword": "2002"}}],
    )

    documents: list[Document] = retriever.invoke("生日聚餐")

    client = retriever._vector_service._store.client
    assert len(documents) == 2
    assert client.calls[0][1]["size"] == 30
    assert client.calls[0][1]["retriever"]["rrf"]["retrievers"][0]["standard"]["filter"] == [
        {"term": {"metadata.shop_id.keyword": "2002"}}
    ]
    assert client.calls[0][1]["retriever"]["rrf"]["retrievers"][1]["knn"]["filter"] == [
        {"term": {"metadata.shop_id.keyword": "2002"}}
    ]
