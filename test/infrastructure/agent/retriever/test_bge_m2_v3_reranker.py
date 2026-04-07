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

from infrastructure.agent.retriever.bge_v2_m3_reranker import BgeV2M3Reranker


class _FakeResponse:
    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload or {
            "results": [
                {"index": 1, "relevance_score": 0.97},
                {"index": 0, "relevance_score": 0.62},
            ]
        }

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args: object, response_payload: dict | None = None, **kwargs: object) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._response_payload = response_payload

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = exc_type
        _ = exc
        _ = tb

    async def post(self, url: str, json: dict) -> _FakeResponse:
        self.calls.append((url, json))
        return _FakeResponse(self._response_payload)


def test_bge_m2_v3_reranker_reorders_documents(monkeypatch) -> None:
    reranker = BgeV2M3Reranker()
    documents = [
        Document(page_content="适合约会", metadata={"id": "1"}),
        Document(page_content="生日布置很细致", metadata={"id": "2"}),
        Document(page_content="这家海底捞的拉面表演不错", metadata={"id": "3"}),
    ]

    reranked = asyncio.run(reranker.rerank("生日", documents))

    assert reranked[0].metadata["id"] == "2"
    print([document.page_content for document in reranked])


def test_bge__rm2_v3_ranker_appends_unranked_documents_after_unique_ranked_results(monkeypatch) -> None:
    import infrastructure.agent.retriever.bge_v2_m3_reranker as reranker_module

    fake_client = _FakeAsyncClient(
        response_payload={
            "results": [
                {"index": 1, "relevance_score": 0.97},
                {"index": 1, "relevance_score": 0.96},
                {"index": 5, "relevance_score": 0.80},
            ]
        }
    )
    monkeypatch.setattr(reranker_module.httpx, "AsyncClient", lambda *args, **kwargs: fake_client)

    reranker = BgeV2M3Reranker()
    documents = [
        Document(page_content="适合约会", metadata={"id": "1"}),
        Document(page_content="生日布置很细致", metadata={"id": "2"}),
        Document(page_content="有包厢", metadata={"id": "3"}),
    ]

    reranked = asyncio.run(reranker.rerank("生日", documents))

    assert [document.metadata["id"] for document in reranked] == ["2", "1", "3"]
