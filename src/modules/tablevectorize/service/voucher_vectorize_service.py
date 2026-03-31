"""Voucher vectorization service for table change events."""

from langchain_core.documents import Document

from common.app_config import app_config
from infrastructure.vector.vector_service import VectorService
from modules.tablevectorize.model.dto.voucher_vectorize_dto import VoucherVectorizeDto


class VoucherVectorizeService:
    """Handle voucher vector upsert and delete operations in vector store."""

    def __init__(self) -> None:
        """Initialize vector service with configured voucher index."""
        self.vector_service: VectorService = VectorService(app_config.voucher_index_name)

    async def handle_message(self, dto: VoucherVectorizeDto) -> None:
        """Handle one voucher vectorize event by operation type."""
        operation: str = dto.operation.strip().lower()
        if operation == "delete":
            await self.vector_service.delete_vector_by_id(dto.id)
            return

        await self.vector_service.delete_vector_by_id(dto.id)
        enrich_text: str = (
            f"商铺“{dto.shop_name}”有团购券可以购买：名称{dto.title}。"
            f"描述：{dto.description}。"
            f"适用规则：{dto.rules}。"
        )
        document: Document = Document(
            page_content=enrich_text,
            metadata={
                "id": str(dto.id),
                "kb_id": str(dto.id),
                "shop_id": str(dto.shop_id),
                "status": dto.status,
                "h3hex": dto.h3hex,
            },
        )
        await self.vector_service.add_documents([document])
