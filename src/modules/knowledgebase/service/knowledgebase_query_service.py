from typing import Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStoreRetriever

from common.exceptions import BusinessException, ErrorCode
from modules.knowledgebase.model.emum.knowledgebase_category_enum import KnowledgebaseCategoryEnum
from modules.knowledgebase.service.knowledgebase_shop_vector_service import KnowledgeBaseShopVectorService
from modules.knowledgebase.service.knowledgebase_voucher_vector_service import KnowledgeBaseVoucherVectorService


class KnowledgeBaseQueryService:
    """VectorService的包装类"""
    def __init__(
        self,
        shop_vector_service: KnowledgeBaseShopVectorService,
        voucher_vector_service: KnowledgeBaseVoucherVectorService,
    ) -> None:
        self._shop_vector_service: KnowledgeBaseShopVectorService = shop_vector_service
        self._voucher_vector_service: KnowledgeBaseVoucherVectorService = voucher_vector_service

    def _get_vector_service(
        self, category: str
    ) -> KnowledgeBaseShopVectorService | KnowledgeBaseVoucherVectorService:
        if category.strip() == "":
            raise BusinessException(ErrorCode.NOT_FOUND, "未知知识库分类", category)
        normalized_category: str = category.strip().lower()
        try:
            category_enum: KnowledgebaseCategoryEnum = KnowledgebaseCategoryEnum(normalized_category)
        except ValueError as exc:
            raise BusinessException(ErrorCode.NOT_FOUND, "未知知识库分类", category) from exc

        if category_enum == KnowledgebaseCategoryEnum.SHOP:
            return self._shop_vector_service
        return self._voucher_vector_service

    async def similar_search(
        self,
        category: str,
        query: str,
        top_k: int,
        min_score: float,
        pre_filter: Optional[list] = None,
    ) -> List[Document]:
        """简单的单分类向量查询"""
        vector_service = self._get_vector_service(category)
        return await vector_service.vector_service.similar_search(
            query,
            top_k,
            min_score,
            pre_filter,
        )

    def get_retriever(
        self,
        category: str,
        search_type: str = "similarity_score_threshold",
        search_kwargs: Optional[dict] = None,
    ) -> VectorStoreRetriever:
        """复杂查询提供retriever让用户自行构建"""
        vector_service = self._get_vector_service(category)
        return vector_service.vector_service.get_retriever(search_type, search_kwargs)

    def get_rrf_retriever(
        self,
        category: str,
        rrf_rule: str,
        content_field: str,
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> VectorStoreRetriever:
        """获取RRF retriever"""
        vector_service = self._get_vector_service(category)
        return vector_service.vector_service.get_rrf_retriever(rrf_rule, content_field, field_mapping)
