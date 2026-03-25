import logging
from typing import List, Optional, Dict

from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore, VectorStoreRetriever
from langchain_elasticsearch import AsyncElasticsearchRetriever

from common.app_config import app_config
from infrastructure.knowledgebase.model.emum.knowledgebase_category_enum import KnowledgebaseCategoryEnum
from infrastructure.vector.vector_store import create_vector_store_with_category, get_vector_index_name

logger = logging.getLogger(__name__)


class VectorService:
    """
    向量端口服务（Port）。

    对业务层暴露与底层向量库无关的方法：
    - add_documents
    - similar_search
    - delete_by_kb_id

    当前默认持有 Elasticsearch 的 VectorStore，后续替换向量库仅需在 VectorStore 侧调整。
    """

    def __init__(self) -> None:
        vectorstore_dict: Dict[str, VectorStore] = {}
        for category_enum in KnowledgebaseCategoryEnum:
            category_str = category_enum.value
            vectorstore_dict[category_str] = create_vector_store_with_category(category_str)
        self._store: Dict[str,VectorStore] = vectorstore_dict

    async def add_documents(self, category: str, documents: List[Document]) -> None:
        await self._store[category].aadd_documents(documents)

    def get_retriever(self, category: str ,search_type: str = "similarity_score_threshold", search_kwargs: Optional[dict] = None) -> VectorStoreRetriever:
        return self._store[category].as_retriever(search_type=search_type, search_kwargs=search_kwargs)

    def get_rrf_retriever(self, category: str, rrf_rule: str, content_field: str, field_mapping: Optional[Dict[str,str]] = None) -> VectorStoreRetriever:
        return AsyncElasticsearchRetriever.from_es_params(
            index_name=get_vector_index_name(category),
            body_func=rrf_rule,
            content_field=content_field,  # 指定返回给 AI 的主要文本字段
            selection_conf=field_mapping,
            es_client=self._store[category].client,
        )

    async def similar_search(
        self,
        category: str,
        query: str,
        top_k: int,
        min_score: float,
        pre_filter: Optional[list] = None,
    ) -> List[Document]:
        """单路召回"""
        try:
            search_kwargs = {
                "k": max(top_k, 1),
                "score_threshold": min_score,
            }
            if pre_filter is not None:
                search_kwargs["filter"] = pre_filter

            retriever = self.get_retriever(category, search_type="similarity_score_threshold", search_kwargs=search_kwargs)
            documents = await retriever.ainvoke(query)
            return documents[:top_k]
        except Exception as e:
            logger.warning("向量搜索失败: %s", str(e))
            raise e

    async def delete_by_kb_id(self, category: str, knowledgebase_id: int) -> None:
        """WARN: 该函数只有Elasticsearch可用"""
        es_client = self._store[category].client
        await es_client.delete_by_query(
            index=app_config.elasticsearch_index_name,
            body={
                "query": {
                    "term": {
                        "metadata.kb_id.keyword": str(knowledgebase_id),
                    }
                }
            },
            refresh=True,
        )

    @staticmethod
    def _build_kb_filter(knowledgebase_ids: List[int]) -> list:
        kb_id_strs = [str(kid) for kid in knowledgebase_ids if kid is not None]
        return [{"terms": {"metadata.kb_id.keyword": kb_id_strs}}]
