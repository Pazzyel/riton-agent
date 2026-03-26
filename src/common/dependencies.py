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
from infrastructure.vector.vector_service import VectorService
from modules.session.repository.chat_session_repository import ChatSessionRepository
from modules.session.service.chat_session_service import ChatSessionService

# ==================== Shared Infrastructure ====================

file_storage_service = FileStorageService()
file_hash_service = FileHashService()
document_parse_service = DocumentParseService()
file_validation_service = FileValidationService()

# ==================== Knowledge Base Module ====================

knowledgebase_repository = KnowledgeBaseRepository()
vector_service = VectorService()
knowledgebase_vector_service = KnowledgeBaseVectorService(vector_service)

knowledgebase_parse_service = KnowledgeBaseParseService(document_parse_service, file_storage_service)
knowledgebase_persistence_service = KnowledgeBasePersistenceService(knowledgebase_repository)
vectorize_message_producer = VectorizeMessageProducer(knowledgebase_repository)
knowledgebase_vectorize_consumer_service = KnowledgeBaseVectorizeConsumerService(
    knowledgebase_repository,
    knowledgebase_vector_service,
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
    knowledgebase_repository, rag_chat_repository, knowledgebase_vector_service, file_storage_service
)
knowledgebase_query_service = KnowledgeBaseQueryService(vector_service)
rag_chat_session_service = RagChatSessionService(rag_chat_session_repository, knowledgebase_query_service)

# ==================== Session Chat Module ====================

chat_session_repository = ChatSessionRepository()
chat_session_service = ChatSessionService(chat_session_repository)
