from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """聊天消息类型枚举。"""

    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ChatMessageEntity:
    """聊天消息实体类。"""

    id: int
    session_id: int
    type: str
    content: str
    message_order: int
    created_at: datetime
    updated_at: datetime
    completed: bool

    def __init__(
        self,
        r_id: int,
        session_id: int,
        r_type: str,
        content: str,
        message_order: int,
        created_at: datetime,
        updated_at: datetime,
        completed: bool,
    ) -> None:
        """初始化聊天消息实体。"""
        self.id = r_id
        self.session_id = session_id
        self.type = r_type
        self.content = content
        self.message_order = message_order
        self.created_at = created_at
        self.updated_at = updated_at
        self.completed = completed


class ChatSessionEntity:
    """聊天会话实体类。"""

    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_pinned: bool

    def __init__(
        self,
        r_id: int,
        title: str,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        message_count: int,
        is_pinned: bool,
    ) -> None:
        """初始化聊天会话实体。"""
        self.id = r_id
        self.title = title
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.message_count = message_count
        self.is_pinned = is_pinned