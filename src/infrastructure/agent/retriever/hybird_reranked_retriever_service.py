import logging

from langchain_core.documents import Document

from infrastructure.agent.retriever.hybrid_es_rrf_retriever import HybridEsRrfRetriever
from infrastructure.agent.retriever.bge_v2_m3_reranker import BgeV2M3Reranker

logger = logging.getLogger(__name__)


class HybirdRerankedRetrieverService:
    """Combine hybrid recall with reranking and graceful degradation."""

    def __init__(
        self,
        hybrid_retriever: HybridEsRrfRetriever,
        reranker: BgeV2M3Reranker,
    ) -> None:
        self._hybrid_retriever: HybridEsRrfRetriever = hybrid_retriever
        self._reranker: BgeV2M3Reranker = reranker

    async def retrieve(
        self,
        query: str,
        top_k: int,
        filters: list[dict] | None = None,
    ) -> list[Document]:
        documents: list[Document] = await self._hybrid_retriever.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
        )
        try:
            return await self._reranker.rerank(query, documents)
        except Exception as exc:
            logger.warning("ollama rerank failed, fallback to hybrid result: %s", str(exc))
            return documents
