"""RocketMQ producer for blog vectorization tasks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from common.app_config import app_config
from infrastructure.mq.abstract_message_producer import AbstractMessageProducer
from modules.tablevectorize.model.dto.blog_vectorize_dto import BlogVectorizeDto


@dataclass
class BlogVectorizeTaskPayload:
    """Payload used by blog vectorization producer."""

    operation: str
    id: int
    shop_id: int
    shop_name: str
    x: float
    y: float
    h3hex: str
    title: str
    images: str
    content: str
    liked: int
    comments: int
    create_time: datetime
    update_time: datetime
    retry_count: int = 0


class BlogVectorizeMessageProducer(AbstractMessageProducer[BlogVectorizeTaskPayload]):
    """Produce blog vectorization messages."""

    def send_vectorize_task(self, dto: BlogVectorizeDto, retry_count: int = 0) -> None:
        """Send one blog vectorize task."""
        self.send_task(
            BlogVectorizeTaskPayload(
                operation=dto.operation,
                id=dto.id,
                shop_id=dto.shop_id,
                shop_name=dto.shop_name,
                x=dto.x,
                y=dto.y,
                h3hex=dto.h3hex,
                title=dto.title,
                images=dto.images,
                content=dto.content,
                liked=dto.liked,
                comments=dto.comments,
                create_time=dto.create_time,
                update_time=dto.update_time,
                retry_count=retry_count,
            )
        )

    def task_display_name(self) -> str:
        """Return display name used in logs."""
        return "Blog vectorize"

    def topic(self) -> str:
        """Return RocketMQ topic."""
        return app_config.blog_vectorize_topic

    def tag(self) -> str:
        """Return RocketMQ tag."""
        return app_config.blog_vectorize_tag

    def build_message(self, payload: BlogVectorizeTaskPayload) -> dict[str, Any]:
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
            "images": payload.images,
            "content": payload.content,
            "liked": payload.liked,
            "comments": payload.comments,
            "createTime": payload.create_time.isoformat(),
            "updateTime": payload.update_time.isoformat(),
            "retryCount": payload.retry_count,
        }

    def payload_identifier(self, payload: BlogVectorizeTaskPayload) -> str:
        """Return payload identifier for logging."""
        return f"blogId={payload.id}"

    def on_send_failed(self, payload: BlogVectorizeTaskPayload, error: str) -> None:
        """Handle message send failures."""
        return None
