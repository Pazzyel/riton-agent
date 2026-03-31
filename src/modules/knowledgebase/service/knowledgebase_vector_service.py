import logging
from typing import Optional

from common.exceptions import BusinessException, ErrorCode
from modules.knowledgebase.service.knowledgebase_shop_vector_service import (
    KnowledgeBaseShopVectorService,
)
from modules.knowledgebase.service.knowledgebase_voucher_vector_service import (
    KnowledgeBaseVoucherVectorService,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseVectorService:
    """
    知识库向量服务兼容层（按分类路由）。
    """

    def __init__(self, vector_service: Optional[object] = None) -> None:
        """
        初始化路由服务（保留兼容签名）。
        """
        _ = vector_service
        self._shop_service: KnowledgeBaseShopVectorService = KnowledgeBaseShopVectorService()
        self._voucher_service: KnowledgeBaseVoucherVectorService = KnowledgeBaseVoucherVectorService()

    def _get_category_service(
        self, kb_category: Optional[str]
    ) -> KnowledgeBaseShopVectorService | KnowledgeBaseVoucherVectorService:
        """
        根据分类返回对应的向量服务。
        """
        if kb_category is None or kb_category.strip() == "":
            raise BusinessException(ErrorCode.NOT_FOUND, "未知知识库分类", kb_category)
        normalized_category: str = kb_category.strip().lower()
        if normalized_category == "shop":
            return self._shop_service
        if normalized_category == "voucher":
            return self._voucher_service
        raise BusinessException(ErrorCode.NOT_FOUND, "未知知识库分类", kb_category)

    async def vectorize_and_store(
        self, kb_id: int, kb_name: str, kb_category: Optional[str], content: str
    ) -> None:
        """
        向量化知识库并存储到 Elasticsearch。
        """
        service = self._get_category_service(kb_category)
        await service.vectorize_and_store(kb_id=kb_id, kb_name=kb_name, content=content)

    async def delete_knowledgebase_by_id(self, knowledgebase_id: int, kb_category: Optional[str] = None) -> None:
        """
        删除指定知识库的所有向量数据。
        通过 metadata 中的 kb_id 字段查询并删除。
        """
        if kb_category is None or kb_category.strip() == "":
            await self._shop_service.delete_knowledgebase_by_id(knowledgebase_id)
            await self._voucher_service.delete_knowledgebase_by_id(knowledgebase_id)
            return

        service = self._get_category_service(kb_category)
        await service.delete_knowledgebase_by_id(knowledgebase_id)
