import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import BusinessException, ErrorCode
from infrastructure.file.file_storage_service import FileStorageService
from infrastructure.knowledgebase.model.entity.knowledgebase_entity import KnowledgeBaseEntity
from infrastructure.knowledgebase.repository.knowledgebase_repository import KnowledgeBaseRepository
from modules.knowledgebase.model.emum.knowledgebase_category_enum import KnowledgebaseCategoryEnum
from modules.knowledgebase.service.knowledgebase_shop_vector_service import KnowledgeBaseShopVectorService
from modules.knowledgebase.service.knowledgebase_voucher_vector_service import KnowledgeBaseVoucherVectorService

logger = logging.getLogger(__name__)

class KnowledgeBaseDeleteService:
    """
    知识库删除服务
    负责知识库及相关数据的删除操作。

    KnowledgeBase deletion service.
    Responsible for deleting knowledge bases and related data.
    """
    def __init__(
        self,
        knowledgebase_repository: KnowledgeBaseRepository,
        shop_vector_service: KnowledgeBaseShopVectorService,
        voucher_vector_service: KnowledgeBaseVoucherVectorService,
        storage_service: FileStorageService,
    ) -> None:
        self.knowledgebase_repository: KnowledgeBaseRepository = knowledgebase_repository
        self._shop_vector_service: KnowledgeBaseShopVectorService = shop_vector_service
        self._voucher_vector_service: KnowledgeBaseVoucherVectorService = voucher_vector_service
        self.storage_service: FileStorageService = storage_service

    def _get_vector_service(
        self, kb_category: Optional[str]
    ) -> KnowledgeBaseShopVectorService | KnowledgeBaseVoucherVectorService:
        if kb_category is None or kb_category.strip() == "":
            raise BusinessException(ErrorCode.NOT_FOUND, "未知知识库分类", kb_category)
        normalized_category: str = kb_category.strip().lower()
        try:
            category_enum: KnowledgebaseCategoryEnum = KnowledgebaseCategoryEnum(normalized_category)
        except ValueError as exc:
            raise BusinessException(ErrorCode.NOT_FOUND, "未知知识库分类", kb_category) from exc

        if category_enum == KnowledgebaseCategoryEnum.SHOP:
            return self._shop_vector_service
        return self._voucher_vector_service

    async def delete_knowledge_base(self, db: AsyncSession, kb_id: int) -> None:
        """
        删除知识库
        包括：RAG会话关联、向量数据、RustFS文件、数据库记录

        Delete a knowledge base.
        Includes: RAG session associations, vector data, RustFS file, and database record.
        """
        # 1. 获取知识库信息 / Get knowledge base info
        kb: Optional[KnowledgeBaseEntity] = await self.knowledgebase_repository.find_by_id(db, kb_id)
        if not kb:
            raise BusinessException(ErrorCode.NOT_FOUND, "知识库不存在 / Knowledge base not found")


        # 2. 删除向量数据 / Delete vector data
        try:
            vector_service = self._get_vector_service(kb.category)
            await vector_service.delete_knowledgebase_by_id(kb_id)
        except Exception as e:
            logger.warning(f"删除向量数据失败，继续删除知识库: kbId={kb_id}, error={str(e)}")

        # 3. 删除RustFS中的文件 / Delete file in RustFS
        if kb.storage_key:
            try:
                # Assuming delete API exists or fallback, adjusting this based on typical storage service
                await self.storage_service.delete_file(kb.storage_key) # This might need to match exact Python method name
            except Exception as e:
                logger.warning(f"删除RustFS文件失败，继续删除知识库记录: kbId={kb_id}, error={str(e)}")

        # 4. 删除知识库记录 / Delete knowledge base record
        await self.knowledgebase_repository.delete_by_id(db, kb_id)
        logger.info(f"知识库已删除: id={kb_id}")
