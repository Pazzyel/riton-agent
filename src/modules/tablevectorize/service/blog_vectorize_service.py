"""Blog vectorization service for table change events."""

from langchain_core.documents import Document

from config.app_config import app_config
from infrastructure.vector.vector_service import VectorService
from modules.tablevectorize.model.dto.blog_vectorize_dto import BlogVectorizeDto
from modules.tablevectorize.service.tablevectorize_text_utils import (
    clean_text,
    is_meaningless_short_text,
    split_text_by_char_limit,
)


class BlogVectorizeService:
    """Handle blog vector upsert and delete operations in vector store."""

    def __init__(self) -> None:
        """Initialize vector service with configured blog index."""
        self.vector_service: VectorService = VectorService(app_config.blog_index_name)

    async def handle_message(self, dto: BlogVectorizeDto) -> None:
        """Handle one blog vectorize event by operation type."""
        operation: str = dto.operation.strip().lower()
        if operation == "DELETE":
            await self.vector_service.delete_vector_by_id(dto.id)
            return

        await self.vector_service.delete_vector_by_id(dto.id)

        cleaned_content: str = clean_text(dto.content)
        if is_meaningless_short_text(cleaned_content):
            return

        chunks: list[str] = split_text_by_char_limit(cleaned_content, 500)
        documents: list[Document] = []
        for chunk_index, chunk in enumerate(chunks):
            enrich_text: str = (
                f"关于店铺“{dto.shop_name}”的评价：标题：《{dto.title}》。内容：{chunk}"
            )
            document: Document = Document(
                page_content=enrich_text,
                metadata={
                    "id": str(dto.id),
                    "kb_id": str(dto.id),
                    "shop_id": str(dto.shop_id),
                    "h3hex": dto.h3hex,
                    "liked": dto.liked,
                    "comments": dto.comments,
                    "chunk_index": chunk_index,
                },
            )
            documents.append(document)

        if documents:
            await self.vector_service.add_documents(documents)
