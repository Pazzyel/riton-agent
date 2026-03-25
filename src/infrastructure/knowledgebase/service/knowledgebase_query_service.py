from langchain_core.documents import Document

from infrastructure.vector.vector_service import VectorService


class KnowledgeBaseQueryService:
    """VectorService的包装类"""
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service

    async def similar_search(self,
         category: str,
         query: str,
         top_k: int,
         min_score: float,
         pre_filter: Optional[list] = None
    ) -> List[Document]:
        """简单的单分类向量查询"""
        return await self.vector_service.similar_search(category, query, top_k, min_score, pre_filter)

    def get_retriever(self, category: str ,search_type: str = "similarity_score_threshold", search_kwargs: Optional[dict] = None) -> VectorStoreRetriever:
        """复杂查询提供retriever让用户自行构建"""
        return self.vector_service.get_retriever(category, search_type, search_kwargs)

    def get_rrf_retriever(self, category: str, rrf_rule: str, content_field: str,
                          field_mapping: Optional[Dict[str, str]] = None) -> VectorStoreRetriever:
        """获取RRF retriever"""
        return self.vector_service.get_rrf_retriever(category, rrf_rule, content_field,field_mapping)