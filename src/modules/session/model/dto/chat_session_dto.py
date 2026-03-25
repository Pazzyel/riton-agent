from datetime import datetime
from typing import List, Optional

from pydantic import Field

from infrastructure.model.BaseCamelSchema import BaseCamelSchema
from modules.knowledgebase.model.knowledgebase_dto import KnowledgeBaseListItemDTO


class CreateSessionRequest(BaseCamelSchema):
    """创建会话请求"""
    title: Optional[str] = None


class UpdateTitleRequest(BaseCamelSchema):
    """更新标题请求"""
    title: str = Field(..., min_length=1)


class SendMessageRequest(BaseCamelSchema):
    """发送消息请求"""
    question: str = Field(..., min_length=1)


class SessionDTO(BaseCamelSchema):
    """会话数据响应"""
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class SessionListItemDTO(BaseCamelSchema):
    """会话列表查询数据响应"""
    id: int
    title: str
    message_count: int
    updated_at: datetime
    is_pinned: bool


class MessageDTO(BaseCamelSchema):
    """消息响应"""
    id: int
    type: str
    content: str
    created_at: datetime


class SessionDetailDTO(BaseCamelSchema):
    """会话详细信息响应，包括消息"""
    id: int
    title: str
    messages: List[MessageDTO]
    created_at: datetime
    updated_at: datetime

