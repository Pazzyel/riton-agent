from typing import List

from pydantic_settings import BaseSettings


class AppConfigProperties(BaseSettings):
    # RocketMQ config
    rocketmq_endpoints: str = "localhost:8081"
    rocketmq_max_retry_count: int = 3

    # DataBase config
    database_url: str = "mysql+aiomysql://root:123@localhost:3308/interview"
    DB_URI: str = "mysql+aiomysql://root:123@localhost:3308/checkpointer" # 这是LangGraph checkpointer的保存点

    # RustFS (S3 compatible) config
    rustfs_endpoint_url: str = "http://localhost:9000"
    rustfs_access_key: str = "rustfsadmin"
    rustfs_secret_key: str = "rustfsadmin"
    rustfs_region_name: str = "us-east-1"
    rustfs_bucket_name: str = "resources"

    # document parse config
    MAX_PARSE_TIME: float = 60.0 # 最大的文档解析时间是60s

    # Knowledge Base config
    kb_vectorize_topic: str = "kb-vectorize-topic"
    kb_vectorize_tag: str = "vectorize"
    kb_vectorize_consumer_group: str = "kb-vectorize-consumer-group"
    kb_allowed_types: list[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    ]
    kb_max_file_size_bytes: int = 50 * 1024 * 1024  # 50MB
    rustfs_kb_bucket_name: str = "knowledgebases"

    # Tokenizer
    tokenizer_name: str = "cl100k_base"

    # ElasticSearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index_name: str = "smart_service"
    elasticsearch_query_mode: str = "dense_vector"

    class Config:
        env_file = ".env"

app_config = AppConfigProperties()
