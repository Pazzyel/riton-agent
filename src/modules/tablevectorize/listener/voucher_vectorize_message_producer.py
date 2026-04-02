"""RocketMQ producer for voucher vectorization tasks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config.app_config import app_config
from infrastructure.mq.abstract_message_producer import AbstractMessageProducer
from modules.tablevectorize.model.dto.voucher_vectorize_dto import VoucherVectorizeDto


@dataclass
class VoucherVectorizeTaskPayload:
    """Payload used by voucher vectorization producer."""

    operation: str
    id: int
    shop_id: int
    shop_name: str
    x: float
    y: float
    h3hex: str
    title: str
    description: str
    rules: str
    pay_value: int
    actual_value: int
    type: int
    status: int
    create_time: datetime
    update_time: datetime
    daily_limit: int
    retry_count: int = 0


class VoucherVectorizeMessageProducer(AbstractMessageProducer[VoucherVectorizeTaskPayload]):
    """Produce voucher vectorization messages."""

    def send_vectorize_task(self, dto: VoucherVectorizeDto, retry_count: int = 0) -> None:
        """Send one voucher vectorize task."""
        self.send_task(
            VoucherVectorizeTaskPayload(
                operation=dto.operation,
                id=dto.id,
                shop_id=dto.shop_id,
                shop_name=dto.shop_name,
                x=dto.x,
                y=dto.y,
                h3hex=dto.h3hex,
                title=dto.title,
                description=dto.description,
                rules=dto.rules,
                pay_value=dto.pay_value,
                actual_value=dto.actual_value,
                type=dto.type,
                status=dto.status,
                create_time=dto.create_time,
                update_time=dto.update_time,
                daily_limit=dto.daily_limit,
                retry_count=retry_count,
            )
        )

    def task_display_name(self) -> str:
        """Return display name used in logs."""
        return "Voucher vectorize"

    def topic(self) -> str:
        """Return RocketMQ topic."""
        return app_config.voucher_vectorize_topic

    def tag(self) -> str:
        """Return RocketMQ tag."""
        return app_config.voucher_vectorize_tag

    def build_message(self, payload: VoucherVectorizeTaskPayload) -> dict[str, Any]:
        """Build mq message payload in camelCase."""
        return {
            "operation": payload.operation,
            "id": payload.id,
            "shopId": payload.shop_id,
            "shopName": payload.shop_name,
            "x": payload.x,
            "y": payload.y,
            "h3hex": payload.h3hex,
            "title": payload.title,
            "description": payload.description,
            "rules": payload.rules,
            "payValue": payload.pay_value,
            "actualValue": payload.actual_value,
            "type": payload.type,
            "status": payload.status,
            "createTime": payload.create_time.isoformat(),
            "updateTime": payload.update_time.isoformat(),
            "dailyLimit": payload.daily_limit,
            "retryCount": payload.retry_count,
        }

    def payload_identifier(self, payload: VoucherVectorizeTaskPayload) -> str:
        """Return payload identifier for logging."""
        return f"voucherId={payload.id}"

    def on_send_failed(self, payload: VoucherVectorizeTaskPayload, error: str) -> None:
        """Handle message send failures."""
        return None
