from langchain_core.vectorstores.base import VectorStore
from langchain_elasticsearch import AsyncElasticsearchStore, AsyncDenseVectorStrategy

from common.ai_config import ai_config
from common.app_config import app_config


def create_vector_store(index_url: str) -> VectorStore:
    """Create a vector store using a full index URL."""
    return AsyncElasticsearchStore(
        es_url=app_config.elasticsearch_url,
        index_name=index_url,
        embedding=ai_config.category_embedding,
        strategy=AsyncDenseVectorStrategy(),
    )
