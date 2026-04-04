"""RocketMQ consumer for blog vectorization messages."""

import logging
from typing import Any, Coroutine, Optional

from pydantic import ValidationError

from config.app_config import app_config
from infrastructure.mq.abstract_stream_consumer import AbstractStreamConsumer
from modules.table_vectorize.listener.blog_vectorize_message_producer import BlogVectorizeMessageProducer
from modules.table_vectorize.model.dto.blog_vectorize_dto import BlogVectorizeDto
from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService

logger = logging.getLogger(__name__)


class BlogVectorizeMessageConsumer(AbstractStreamConsumer[BlogVectorizeDto]):
    """Consume blog vectorization messages and delegate to service."""

    def __init__(
        self,
        blog_vectorize_service: BlogVectorizeService,
        blog_vectorize_message_producer: BlogVectorizeMessageProducer,
    ) -> None:
        """Initialize consumer dependencies."""
        super().__init__()
        self._blog_vectorize_service: BlogVectorizeService = blog_vectorize_service
        self._blog_vectorize_message_producer: BlogVectorizeMessageProducer = blog_vectorize_message_producer

    def consumer_display_name(self) -> str:
        """Return display name used in logs."""
        return "Blog vectorize"

    def consumer_group(self) -> str:
        """Return configured consumer group."""
        return app_config.blog_vectorize_consumer_group

    def topic(self) -> str:
        """Return configured topic."""
        return app_config.blog_vectorize_topic

    def tag(self) -> str:
        """Return configured tag."""
        return app_config.blog_vectorize_tag

    def parse_payload(self, payload_dict: Any) -> Optional[BlogVectorizeDto]:
        """Parse and validate payload dictionary into DTO."""
        try:
            dto: BlogVectorizeDto = BlogVectorizeDto.model_validate(payload_dict)
        except ValidationError:
            logger.warning("Blog vectorize message missing required fields: %s", payload_dict)
            return None

        if getattr(dto, "retry_count", None) is None:
            dto = dto.model_copy(update={"retry_count": 0})
        return dto

    def process_payload(self, payload: BlogVectorizeDto) -> Coroutine[Any, Any, None]:
        """Delegate payload processing to blog vectorize service."""
        return self._blog_vectorize_service.handle_message(payload)

    def requeue_payload(self, payload: BlogVectorizeDto, retry_count: int) -> None:
        """Requeue message using producer with updated retry count."""
        self._blog_vectorize_message_producer.send_vectorize_task(payload, retry_count=retry_count)

    async def mark_failed(self, payload: BlogVectorizeDto, error_message: str) -> None:
        """Handle final message failure without persistence side effects."""
        logger.error("Blog vectorize task failed permanently: id=%s, error=%s", payload.id, error_message)

    def payload_retry_count(self, payload: BlogVectorizeDto) -> int:
        """Return payload retry count with safe default."""
        return int(getattr(payload, "retry_count", 0) or 0)

    def payload_identifier(self, payload: BlogVectorizeDto) -> str:
        """Return payload identifier for logging."""
        return f"blogId={payload.id}"
