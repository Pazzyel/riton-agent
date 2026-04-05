from infrastructure.file.document_parse_service import DocumentParseService
from infrastructure.file.file_hash_service import FileHashService
from infrastructure.file.file_storage_service import FileStorageService
from infrastructure.file.file_validation_service import FileValidationService
from modules.knowledgebase.listener import \
    KnowledgeBaseVectorizeConsumerService
from modules.knowledgebase.listener.vectorize_message_consumer import VectorizeMessageConsumer
from modules.knowledgebase.listener.vectorize_message_producer import VectorizeMessageProducer
from modules.knowledgebase.repository import KnowledgeBaseRepository
from modules.knowledgebase.service.knowledgebase_count_service import KnowledgeBaseCountService
from modules.knowledgebase.service.knowledgebase_delete_service import KnowledgeBaseDeleteService
from modules.knowledgebase import KnowledgeBaseListService
from modules.knowledgebase import KnowledgeBaseParseService
from modules.knowledgebase import KnowledgeBasePersistenceService
from modules.knowledgebase.service.knowledgebase_query_service import KnowledgeBaseQueryService
from modules.knowledgebase.service.knowledgebase_upload_service import KnowledgeBaseUploadService
from modules.knowledgebase import KnowledgeBaseVectorService
from modules.knowledgebase.service.knowledgebase_shop_vector_service import KnowledgeBaseShopVectorService
from modules.knowledgebase.service.knowledgebase_voucher_vector_service import KnowledgeBaseVoucherVectorService
from modules.table_vectorize.listener.blog_vectorize_message_consumer import BlogVectorizeMessageConsumer
from modules.table_vectorize.listener.blog_vectorize_message_producer import BlogVectorizeMessageProducer
from modules.table_vectorize.listener.shop_vectorize_message_consumer import ShopVectorizeMessageConsumer
from modules.table_vectorize.listener.shop_vectorize_message_producer import ShopVectorizeMessageProducer
from modules.table_vectorize.listener.voucher_vectorize_message_consumer import (
    VoucherVectorizeMessageConsumer,
)
from modules.table_vectorize.listener.voucher_vectorize_message_producer import (
    VoucherVectorizeMessageProducer,
)
from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService
from modules.table_vectorize.service.shop_vectorize_service import ShopVectorizeService
from modules.table_vectorize.service.voucher_vectorize_service import VoucherVectorizeService
from modules.session.repository.chat_session_repository import ChatSessionRepository
from modules.session.service.chat_session_service import ChatSessionService
from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

# ==================== Shared Infrastructure ====================

file_storage_service = FileStorageService()
file_hash_service = FileHashService()
document_parse_service = DocumentParseService()
file_validation_service = FileValidationService()

# ==================== Knowledge Base Module ====================

knowledgebase_repository = KnowledgeBaseRepository()
knowledgebase_vector_service = KnowledgeBaseVectorService()
knowledgebase_shop_vector_service = KnowledgeBaseShopVectorService()
knowledgebase_voucher_vector_service = KnowledgeBaseVoucherVectorService()

knowledgebase_parse_service = KnowledgeBaseParseService(document_parse_service, file_storage_service)
knowledgebase_persistence_service = KnowledgeBasePersistenceService(knowledgebase_repository)
vectorize_message_producer = VectorizeMessageProducer(knowledgebase_repository)
knowledgebase_vectorize_consumer_service = KnowledgeBaseVectorizeConsumerService(
    knowledgebase_repository,
    knowledgebase_vector_service,
    knowledgebase_shop_vector_service,
    knowledgebase_voucher_vector_service,
)
vectorize_message_consumer = VectorizeMessageConsumer(
    knowledgebase_vectorize_consumer_service,
    vectorize_message_producer,
)

knowledgebase_upload_service = KnowledgeBaseUploadService(
    knowledgebase_parse_service,
    knowledgebase_persistence_service,
    file_storage_service,
    knowledgebase_repository,
    file_validation_service,
    file_hash_service,
    vectorize_message_producer,
)

knowledgebase_list_service = KnowledgeBaseListService(
    knowledgebase_repository, file_storage_service
)
knowledgebase_count_service = KnowledgeBaseCountService(knowledgebase_repository)
knowledgebase_delete_service = KnowledgeBaseDeleteService(
    knowledgebase_repository,
    knowledgebase_shop_vector_service,
    knowledgebase_voucher_vector_service,
    file_storage_service,
)
knowledgebase_query_service = KnowledgeBaseQueryService(
    knowledgebase_shop_vector_service,
    knowledgebase_voucher_vector_service,
)

# ==================== Table Vectorize Module ====================

shop_vectorize_service = ShopVectorizeService()
voucher_vectorize_service = VoucherVectorizeService()
blog_vectorize_service = BlogVectorizeService()

shop_vectorize_message_producer = ShopVectorizeMessageProducer()
voucher_vectorize_message_producer = VoucherVectorizeMessageProducer()
blog_vectorize_message_producer = BlogVectorizeMessageProducer()

shop_vectorize_message_consumer = ShopVectorizeMessageConsumer(
    shop_vectorize_service,
    shop_vectorize_message_producer,
)
voucher_vectorize_message_consumer = VoucherVectorizeMessageConsumer(
    voucher_vectorize_service,
    voucher_vectorize_message_producer,
)
blog_vectorize_message_consumer = BlogVectorizeMessageConsumer(
    blog_vectorize_service,
    blog_vectorize_message_producer,
)

# ==================== Session Chat Module ====================

chat_session_repository = ChatSessionRepository()
chat_session_service = ChatSessionService(chat_session_repository)

# ==================== Shop Search Module ====================

shop_search_tool_service = ShopSearchToolService()
shop_search_rag_service = ShopSearchRagService(blog_vectorize_service)
shop_search_agent_service = ShopSearchAgentService(
    shop_search_tool_service,
    shop_search_rag_service,
    chat_session_service,
)
