import asyncio

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from infrastructure.vector.vector_service import VectorService


class HybridEsRrfRetriever(BaseRetriever):
    """Elasticsearch hybrid retriever using keyword + vector RRF fusion."""

    _vector_service: VectorService
    _content_field: str
    _vector_field: str
    _rank_constant: int
    _default_top_k: int
    _default_filters: list[dict]

    def __init__(
        self,
        vector_service: VectorService,
        content_field: str = "text",
        vector_field: str = "vector",
        rank_constant: int = 60,
        default_top_k: int = 8,
        default_filters: list[dict] | None = None,
    ) -> None:
        super().__init__()
        self._vector_service: VectorService = vector_service
        self._content_field: str = content_field
        self._vector_field: str = vector_field
        self._rank_constant: int = rank_constant
        self._default_top_k: int = default_top_k
        self._default_filters: list[dict] = list(default_filters or [])

    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        _ = run_manager
        return asyncio.run(
            self.retrieve(
                query=query,
                top_k=self._default_top_k,
                filters=list(self._default_filters),
            )
        )

    async def _aget_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        _ = run_manager
        return await self.retrieve(
            query=query,
            top_k=self._default_top_k,
            filters=list(self._default_filters),
        )

    async def retrieve(
        self,
        query: str,
        top_k: int,
        filters: list[dict] | None = None,
    ) -> list[Document]:
        """混合检索，RRF融合"""
        # 召回量是最终结果的10倍，rerank后筛选
        candidate_k: int = max(top_k * 10, top_k, 1)
        # 获取查询文本的向量
        query_vector: list[float] = await self._vector_service._store.embedding.aembed_query(query)
        body: dict = self._build_body(
            query=query,
            query_vector=query_vector,
            candidate_k=candidate_k,
            filters=filters or [],
        )
        response: dict = await self._vector_service._store.client.search(
            index=self._vector_service._index_url,
            body=body,
        )
        return self._to_documents(response)

    def _build_body(
        self,
        query: str,
        query_vector: list[float],
        candidate_k: int,
        filters: list[dict],
    ) -> dict:
        """构建ES RRF查询的JSON请求体"""
        return {
            "size": candidate_k,
            "retriever": {
                "rrf": {
                    "rank_window_size": candidate_k,
                    "rank_constant": self._rank_constant,
                    "retrievers": [
                        {
                            "standard": {
                                "query": {
                                    "match": {
                                        self._content_field: { # 默认为"text"
                                            "query": query,
                                        }
                                    }
                                },
                                "filter": filters,
                            }
                        },
                        {
                            "knn": {
                                "field": self._vector_field, # 默认为"vector"
                                "query_vector": query_vector,
                                "k": candidate_k,
                                "filter": filters,
                            }
                        },
                    ],
                }
            },
        }

    def _to_documents(self, response: dict) -> list[Document]:
        """从ES返回的JSON提取出List[Document]"""
        hits: list[dict] = response.get("hits", {}).get("hits", [])
        documents: list[Document] = []
        for hit in hits:
            source: dict = hit.get("_source", {})
            page_content: str = str(source.get(self._content_field, ""))
            metadata: dict = source.get("metadata", {})
            documents.append(Document(page_content=page_content, metadata=metadata))
        return documents
