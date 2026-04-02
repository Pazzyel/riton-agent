"""RocketMQ producer for shop vectorization tasks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config.app_config import app_config
from infrastructure.mq.abstract_message_producer import AbstractMessageProducer
from modules.tablevectorize.model.dto.shop_vectorize_dto import ShopVectorizeDto


@dataclass
class ShopVectorizeTaskPayload:
    """Payload used by shop vectorization producer."""

    operation: str
    id: int
    name: str
    type_name: str
    description: str
    images: str
    area: str
    address: str
    x: float
    y: float
    h3hex: str
    avg_price: int
    sold: int
    comments: int
    score: int
    open_hours: str
    create_time: datetime
    update_time: datetime
    retry_count: int = 0


class ShopVectorizeMessageProducer(AbstractMessageProducer[ShopVectorizeTaskPayload]):
    """Produce shop vectorization messages."""

    def send_vectorize_task(self, dto: ShopVectorizeDto, retry_count: int = 0) -> None:
        """Send one shop vectorize task."""
        self.send_task(
            ShopVectorizeTaskPayload(
                operation=dto.operation,
                id=dto.id,
                name=dto.name,
                type_name=dto.type_name,
                description=dto.description,
                images=dto.images,
                area=dto.area,
                address=dto.address,
                x=dto.x,
                y=dto.y,
                h3hex=dto.h3hex,
                avg_price=dto.avg_price,
                sold=dto.sold,
                comments=dto.comments,
                score=dto.score,
                open_hours=dto.open_hours,
                create_time=dto.create_time,
                update_time=dto.update_time,
                retry_count=retry_count,
            )
        )

    def task_display_name(self) -> str:
        """Return display name used in logs."""
        return "Shop vectorize"

    def topic(self) -> str:
        """Return RocketMQ topic."""
        return app_config.shop_vectorize_topic

    def tag(self) -> str:
        """Return RocketMQ tag."""
        return app_config.shop_vectorize_tag

    def build_message(self, payload: ShopVectorizeTaskPayload) -> dict[str, Any]:
        """Build mq message payload in camelCase."""
        return {
            "operation": payload.operation,
            "id": payload.id,
            "name": payload.name,
            "typeName": payload.type_name,
            "description": payload.description,
            "images": payload.images,
            "area": payload.area,
            "address": payload.address,
            "x": payload.x,
            "y": payload.y,
            "h3hex": payload.h3hex,
            "avgPrice": payload.avg_price,
            "sold": payload.sold,
            "comments": payload.comments,
            "score": payload.score,
            "openHours": payload.open_hours,
            "createTime": payload.create_time.isoformat(),
            "updateTime": payload.update_time.isoformat(),
            "retryCount": payload.retry_count,
        }

    def payload_identifier(self, payload: ShopVectorizeTaskPayload) -> str:
        """Return payload identifier for logging."""
        return f"shopId={payload.id}"

    def on_send_failed(self, payload: ShopVectorizeTaskPayload, error: str) -> None:
        """Handle message send failures."""
        return None
