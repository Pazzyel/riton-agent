from langchain_core.vectorstores.base import VectorStore
from langchain_elasticsearch import AsyncElasticsearchStore, AsyncDenseVectorStrategy

from common.ai_config import ai_config
from common.app_config import app_config


def get_vector_index_name(prefix: str, category: str) -> str:
    return prefix + "/" + category

def create_vector_store_with_category(prefix: str, category: str) -> VectorStore:
    return AsyncElasticsearchStore(
        es_url=app_config.elasticsearch_url,
        index_name=get_vector_index_name(prefix,category),
        embedding=ai_config.category_embedding,
        strategy=AsyncDenseVectorStrategy(),
    )