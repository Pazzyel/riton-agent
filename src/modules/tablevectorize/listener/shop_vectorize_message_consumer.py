"""RocketMQ consumer for shop vectorization messages."""

import logging
from typing import Any, Coroutine, Optional

from pydantic import ValidationError

from config.app_config import app_config
from infrastructure.mq.abstract_stream_consumer import AbstractStreamConsumer
from modules.tablevectorize.listener.shop_vectorize_message_producer import ShopVectorizeMessageProducer
from modules.tablevectorize.model.dto.shop_vectorize_dto import ShopVectorizeDto
from modules.tablevectorize.service.shop_vectorize_service import ShopVectorizeService

logger = logging.getLogger(__name__)


class ShopVectorizeMessageConsumer(AbstractStreamConsumer[ShopVectorizeDto]):
    """Consume shop vectorization messages and delegate to service."""

    def __init__(
        self,
        shop_vectorize_service: ShopVectorizeService,
        shop_vectorize_message_producer: ShopVectorizeMessageProducer,
    ) -> None:
        """Initialize consumer dependencies."""
        super().__init__()
        self._shop_vectorize_service: ShopVectorizeService = shop_vectorize_service
        self._shop_vectorize_message_producer: ShopVectorizeMessageProducer = shop_vectorize_message_producer

    def consumer_display_name(self) -> str:
        """Return display name used in logs."""
        return "Shop vectorize"

    def consumer_group(self) -> str:
        """Return configured consumer group."""
        return app_config.shop_vectorize_consumer_group

    def topic(self) -> str:
        """Return configured topic."""
        return app_config.shop_vectorize_topic

    def tag(self) -> str:
        """Return configured tag."""
        return app_config.shop_vectorize_tag

    def parse_payload(self, payload_dict: Any) -> Optional[ShopVectorizeDto]:
        """Parse and validate payload dictionary into DTO."""
        try:
            dto: ShopVectorizeDto = ShopVectorizeDto.model_validate(payload_dict)
        except ValidationError:
            logger.warning("Shop vectorize message missing required fields: %s", payload_dict)
            return None

        if getattr(dto, "retry_count", None) is None:
            dto = dto.model_copy(update={"retry_count": 0})
        return dto

    def process_payload(self, payload: ShopVectorizeDto) -> Coroutine[Any, Any, None]:
        """Delegate payload processing to shop vectorize service."""
        return self._shop_vectorize_service.handle_message(payload)

    def requeue_payload(self, payload: ShopVectorizeDto, retry_count: int) -> None:
        """Requeue message using producer with updated retry count."""
        self._shop_vectorize_message_producer.send_vectorize_task(payload, retry_count=retry_count)

    async def mark_failed(self, payload: ShopVectorizeDto, error_message: str) -> None:
        """Handle final message failure without persistence side effects."""
        logger.error("Shop vectorize task failed permanently: id=%s, error=%s", payload.id, error_message)

    def payload_retry_count(self, payload: ShopVectorizeDto) -> int:
        """Return payload retry count with safe default."""
        return int(getattr(payload, "retry_count", 0) or 0)

    def payload_identifier(self, payload: ShopVectorizeDto) -> str:
        """Return payload identifier for logging."""
        return f"shopId={payload.id}"
