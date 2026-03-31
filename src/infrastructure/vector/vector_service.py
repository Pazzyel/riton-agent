import logging
from typing import List, Optional, Dict

from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore, VectorStoreRetriever
from langchain_elasticsearch import AsyncElasticsearchRetriever

from infrastructure.vector.vector_store import create_vector_store

logger = logging.getLogger(__name__)


class VectorService:
    """
    向量端口服务（Port）。
    """

    def __init__(self, index_url: str) -> None:
        self._index_url: str = index_url
        self._store: VectorStore = create_vector_store(index_url)

    async def add_documents(self, documents: List[Document]) -> None:
        await self._store.aadd_documents(documents)

    def get_retriever(
        self,
        search_type: str = "similarity_score_threshold",
        search_kwargs: Optional[dict] = None,
    ) -> VectorStoreRetriever:
        return self._store.as_retriever(search_type=search_type, search_kwargs=search_kwargs)

    def get_rrf_retriever(
        self,
        rrf_rule: str,
        content_field: str,
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> VectorStoreRetriever:
        return AsyncElasticsearchRetriever.from_es_params(
            index_name=self._index_url,
            body_func=rrf_rule,
            content_field=content_field,
            selection_conf=field_mapping,
            es_client=self._store.client,
        )

    async def similar_search(
        self,
        query: str,
        top_k: int,
        min_score: float,
        pre_filter: Optional[list] = None,
    ) -> List[Document]:
        try:
            search_kwargs = {
                "k": max(top_k, 1),
                "score_threshold": min_score,
            }
            if pre_filter is not None:
                search_kwargs["filter"] = pre_filter

            retriever = self.get_retriever(
                search_type="similarity_score_threshold",
                search_kwargs=search_kwargs,
            )
            documents = await retriever.ainvoke(query)
            return documents[:top_k]
        except Exception as e:
            logger.warning("向量搜索失败: %s", str(e))
            raise e

    async def delete_vector_by_id(self, vector_id: int) -> None:
        """WARN: 该函数只有Elasticsearch可用"""
        es_client = self._store.client
        await es_client.delete_by_query(
            index=self._index_url,
            body={
                "query": {
                    "term": {
                        "metadata.kb_id.keyword": str(vector_id),
                    }
                }
            },
            refresh=True,
        )

    @staticmethod
    def _build_kb_filter(ids: List[int]) -> list:
        kb_id_strs = [str(kid) for kid in ids if kid is not None]
        return [{"terms": {"metadata.kb_id.keyword": kb_id_strs}}]
