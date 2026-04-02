from langchain_core.vectorstores.base import VectorStore
from langchain_elasticsearch import AsyncElasticsearchStore, AsyncDenseVectorStrategy

from config.ai_config import ai_config
from config.app_config import app_config


def create_vector_store(index_url: str) -> VectorStore:
    """Create a vector store using a full index URL."""
    return AsyncElasticsearchStore(
        es_url=app_config.elasticsearch_url,
        index_name=index_url,
        embedding=ai_config.category_embedding,
        strategy=AsyncDenseVectorStrategy(),
    )


def get_vector_index_name(prefix: str, category: str) -> str:
    """Build a full vector index name from prefix and category."""
    normalized_prefix: str = prefix.rstrip("/")
    normalized_category: str = category.lstrip("/")
    if not normalized_prefix:
        return normalized_category
    if not normalized_category:
        return normalized_prefix
    return f"{normalized_prefix}/{normalized_category}"


def create_vector_store_with_category(prefix: str, category: str) -> VectorStore:
    """Create a vector store using prefix and category."""
    index_url: str = get_vector_index_name(prefix, category)
    return create_vector_store(index_url)
