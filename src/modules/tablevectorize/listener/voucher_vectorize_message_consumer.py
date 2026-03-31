"""RocketMQ consumer for voucher vectorization messages."""

import logging
from typing import Any, Coroutine, Optional

from pydantic import ValidationError

from common.app_config import app_config
from infrastructure.mq.abstract_stream_consumer import AbstractStreamConsumer
from modules.tablevectorize.listener.voucher_vectorize_message_producer import (
    VoucherVectorizeMessageProducer,
)
from modules.tablevectorize.model.dto.voucher_vectorize_dto import VoucherVectorizeDto
from modules.tablevectorize.service.voucher_vectorize_service import VoucherVectorizeService

logger = logging.getLogger(__name__)


class VoucherVectorizeMessageConsumer(AbstractStreamConsumer[VoucherVectorizeDto]):
    """Consume voucher vectorization messages and delegate to service."""

    def __init__(
        self,
        voucher_vectorize_service: VoucherVectorizeService,
        voucher_vectorize_message_producer: VoucherVectorizeMessageProducer,
    ) -> None:
        """Initialize consumer dependencies."""
        super().__init__()
        self._voucher_vectorize_service: VoucherVectorizeService = voucher_vectorize_service
        self._voucher_vectorize_message_producer: VoucherVectorizeMessageProducer = (
            voucher_vectorize_message_producer
        )

    def consumer_display_name(self) -> str:
        """Return display name used in logs."""
        return "Voucher vectorize"

    def consumer_group(self) -> str:
        """Return configured consumer group."""
        return app_config.voucher_vectorize_consumer_group

    def topic(self) -> str:
        """Return configured topic."""
        return app_config.voucher_vectorize_topic

    def tag(self) -> str:
        """Return configured tag."""
        return app_config.voucher_vectorize_tag

    def parse_payload(self, payload_dict: Any) -> Optional[VoucherVectorizeDto]:
        """Parse and validate payload dictionary into DTO."""
        try:
            dto: VoucherVectorizeDto = VoucherVectorizeDto.model_validate(payload_dict)
        except ValidationError:
            logger.warning("Voucher vectorize message missing required fields: %s", payload_dict)
            return None

        if getattr(dto, "retry_count", None) is None:
            dto = dto.model_copy(update={"retry_count": 0})
        return dto

    def process_payload(self, payload: VoucherVectorizeDto) -> Coroutine[Any, Any, None]:
        """Delegate payload processing to voucher vectorize service."""
        return self._voucher_vectorize_service.handle_message(payload)

    def requeue_payload(self, payload: VoucherVectorizeDto, retry_count: int) -> None:
        """Requeue message using producer with updated retry count."""
        self._voucher_vectorize_message_producer.send_vectorize_task(payload, retry_count=retry_count)

    async def mark_failed(self, payload: VoucherVectorizeDto, error_message: str) -> None:
        """Handle final message failure without persistence side effects."""
        logger.error("Voucher vectorize task failed permanently: id=%s, error=%s", payload.id, error_message)

    def payload_retry_count(self, payload: VoucherVectorizeDto) -> int:
        """Return payload retry count with safe default."""
        return int(getattr(payload, "retry_count", 0) or 0)

    def payload_identifier(self, payload: VoucherVectorizeDto) -> str:
        """Return payload identifier for logging."""
        return f"voucherId={payload.id}"
