import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sklearn.utils import deprecated
from sqlalchemy.ext.asyncio import AsyncSession

from common.dependencies import chat_session_service
from common.models import Result
from infrastructure.database.connection import get_async_session
from modules.session.model.dto.chat_session_dto import (
    CreateSessionRequest,
    SessionDTO,
    SessionDetailDTO,
    SessionListItemDTO,
    SendMessageRequest,
    UpdateTitleRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/sessions", response_model=Result[SessionDTO])
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_async_session),
) -> Result[SessionDTO]:
    """创建聊天请求"""
    logger.info("创建聊天请求 Request arrived: POST /api/chat/sessions")
    data: SessionDTO = await chat_session_service.create_session(db, request)
    return Result.success(data=data)


@router.get("/sessions", response_model=Result[list[SessionListItemDTO]])
async def list_sessions(
    db: AsyncSession = Depends(get_async_session),
) -> Result[list[SessionListItemDTO]]:
    """获取聊天列表请求"""
    logger.info("获取聊天列表请求 Request arrived: GET /api/chat/sessions")
    data: list[SessionListItemDTO] = await chat_session_service.list_sessions(db)
    return Result.success(data=data)


@router.get("/sessions/{session_id}", response_model=Result[SessionDetailDTO])
async def get_session_detail(
    session_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> Result[SessionDetailDTO]:
    """获取单个聊天详情信息"""
    logger.info("获取单个聊天详情信息 Request arrived: GET /api/chat/sessions/%s", session_id)
    data: SessionDetailDTO = await chat_session_service.get_session_detail(db, session_id)
    return Result.success(data=data)


@router.put("/sessions/{session_id}/title", response_model=Result[None])
async def update_session_title(
    session_id: int,
    request: UpdateTitleRequest,
    db: AsyncSession = Depends(get_async_session),
) -> Result[None]:
    """更新聊天标题请求"""
    logger.info("更新聊天标题请求 Request arrived: PUT /api/chat/sessions/%s/title", session_id)
    await chat_session_service.update_session_title(db, session_id, request.title)
    return Result.success(data=None)


@router.put("/sessions/{session_id}/pin", response_model=Result[None])
async def toggle_pin(
    session_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> Result[None]:
    """置顶聊天"""
    logger.info("置顶聊天 Request arrived: PUT /api/chat/sessions/%s/pin", session_id)
    await chat_session_service.toggle_pin(db, session_id)
    return Result.success(data=None)

@router.delete("/sessions/{session_id}", response_model=Result[None])
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> Result[None]:
    """删除聊天"""
    logger.info("删除聊天 Request arrived: DELETE /api/chat/sessions/%s", session_id)
    await chat_session_service.delete_session(db, session_id)
    return Result.success(data=None)


@deprecated
@router.post("/sessions/{session_id}/messages/stream", response_model=None)
async def send_message_stream(
    session_id: int,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """请求流式AI消息"""
    logger.info("请求流式AI消息 Request arrived: POST /api/chat/sessions/%s/messages/stream", session_id)
    return StreamingResponse(
        chat_session_service.send_message_stream(db, session_id, request.question),
        media_type="text/event-stream",
    )
