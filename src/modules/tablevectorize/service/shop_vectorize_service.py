"""Shop vectorization service for table change events."""

from langchain_core.documents import Document

from common.app_config import app_config
from infrastructure.vector.vector_service import VectorService
from modules.tablevectorize.model.dto.shop_vectorize_dto import ShopVectorizeDto


class ShopVectorizeService:
    """Handle shop vector upsert/delete operations in vector store."""

    def __init__(self) -> None:
        """Initialize vector service with configured shop index."""
        self.vector_service: VectorService = VectorService(app_config.shop_index_name)

    async def handle_message(self, dto: ShopVectorizeDto) -> None:
        """Handle one shop vectorize event by operation type."""
        operation: str = dto.operation.strip().lower()
        if operation == "DELETE":
            await self.vector_service.delete_vector_by_id(dto.id)
            return

        await self.vector_service.delete_vector_by_id(dto.id)
        enrich_text: str = (
            f"{dto.name}是一家位于{dto.area}商圈，地址在{dto.address}的{dto.type_name}店。"
        )
        document: Document = Document(
            page_content=enrich_text,
            metadata={
                "id": str(dto.id),
                "kb_id": str(dto.id),
                "type_name": dto.type_name,
                "h3hex": dto.h3hex,
            },
        )
        await self.vector_service.add_documents([document])
