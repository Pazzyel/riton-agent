import json
import logging
from typing import Any, AsyncGenerator, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import BusinessException, ErrorCode
from modules.session.model.dto.chat_session_dto import (
    CreateSessionRequest,
    MessageDTO,
    SessionDTO,
    SessionDetailDTO,
    SessionListItemDTO,
)
from modules.session.model.entity.chat_message_entity import ChatMessageEntity, ChatSessionEntity
from modules.session.repository.chat_session_repository import ChatSessionRepository

logger = logging.getLogger(__name__)


class ChatSessionService:
    """聊天会话业务层。"""

    def __init__(self, chat_session_repository: ChatSessionRepository) -> None:
        """初始化聊天会话业务层。"""
        self.chat_session_repository: ChatSessionRepository = chat_session_repository

    async def create_session(self, db: AsyncSession, request: CreateSessionRequest) -> SessionDTO:
        """创建聊天会话。"""
        title: str = self._resolve_title(request.title)
        session_entity: ChatSessionEntity = await self.chat_session_repository.create_session(db, title)

        logger.info("创建聊天会话: id=%d, title=%s", session_entity.id, session_entity.title)
        return SessionDTO(
            id=session_entity.id,
            title=session_entity.title,
            created_at=session_entity.created_at,
            updated_at=session_entity.updated_at,
        )

    async def list_sessions(self, db: AsyncSession) -> List[SessionListItemDTO]:
        """读取聊天会话列表。"""
        return await self.chat_session_repository.list_sessions(db)

    async def get_session_detail(self, db: AsyncSession, session_id: int) -> SessionDetailDTO:
        """读取单个会话详情与消息列表。"""
        # Step 1: 读取会话
        session_entity: Optional[ChatSessionEntity] = await self.chat_session_repository.get_session_by_id(db, session_id)
        if session_entity is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "会话不存在")

        # Step 2: 读取消息并映射 DTO
        message_entities: List[ChatMessageEntity] = await self.chat_session_repository.get_session_messages(db, session_id)
        messages: List[MessageDTO] = [
            MessageDTO(
                id=item.id,
                type=str(item.type).lower(),
                content=item.content,
                created_at=item.created_at,
            )
            for item in message_entities
        ]

        # Step 3: 组装返回结果
        return SessionDetailDTO(
            id=session_entity.id,
            title=session_entity.title,
            messages=messages,
            created_at=session_entity.created_at,
            updated_at=session_entity.updated_at,
        )

    async def update_session_title(self, db: AsyncSession, session_id: int, title: str) -> None:
        """更新会话标题。"""
        normalized_title: str = self._resolve_title(title)
        updated: bool = await self.chat_session_repository.update_session_title(db, session_id, normalized_title)
        if not updated:
            raise BusinessException(ErrorCode.NOT_FOUND, "会话不存在")
        logger.info("更新会话标题: sessionId=%d, title=%s", session_id, normalized_title)

    async def toggle_pin(self, db: AsyncSession, session_id: int) -> None:
        """切换会话置顶状态。"""
        pinned: Optional[bool] = await self.chat_session_repository.toggle_pin(db, session_id)
        if pinned is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "会话不存在")
        logger.info("切换会话置顶: sessionId=%d, isPinned=%s", session_id, str(pinned))

    async def delete_session(self, db: AsyncSession, session_id: int) -> None:
        """删除会话及其消息。"""
        deleted: bool = await self.chat_session_repository.delete_session(db, session_id)
        if not deleted:
            raise BusinessException(ErrorCode.NOT_FOUND, "会话不存在")
        logger.info("删除会话: sessionId=%d", session_id)

    async def send_message_stream(self, db: AsyncSession, session_id: int, question: str) -> AsyncGenerator[str, None]:
        """完成“预落库 -> 流式输出 -> 回写消息”的聊天流程。"""
        # Step 1: 校验输入并创建消息记录
        normalized_question: str = question.strip()
        if normalized_question == "":
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "问题不能为空")

        message_id: Optional[int] = await self.chat_session_repository.prepare_stream_messages(db, session_id, normalized_question)
        if message_id is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "会话不存在")

        # Step 2: 生成回答并按 SSE 输出
        final_content: str = ""
        try:
            async for chunk in self._generate_answer_stream(normalized_question): # TODO 后续替换为对应Agent
                if chunk == "":
                    continue
                final_content = final_content + chunk
                payload: dict[str, Any] = {"response": final_content}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n"

            if final_content == "":
                final_content = "抱歉，我暂时无法生成回答。"
                payload = {"response": final_content}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n"

            yield "data: [DONE]\\n\\n"
        except Exception as error:
            # Step 3: 异常时返回错误文本并继续回写
            error_message: str = f"抱歉，回答生成失败：{str(error)}"
            final_content = error_message if final_content == "" else final_content
            payload = {"response": final_content}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n"
            yield "data: [DONE]\\n\\n"
        finally:
            # Step 4: 无论成功或失败都回写消息内容
            await self.chat_session_repository.complete_stream_message(db, message_id, final_content)

    async def _generate_answer_stream(self, question: str) -> AsyncGenerator[str, None]:
        """生成回答并分片输出。"""
        # Step 1: 生成完整回答文本
        answer_text: str = self._build_default_answer(question)

        # Step 2: 将完整回答分片成伪流式输出
        for item in self._chunk_text(answer_text, 20):
            yield item

    def _build_default_answer(self, question: str) -> str:
        """构建默认回答文本。"""
        normalized_question: str = question.strip()
        return f"我已收到你的问题：{normalized_question}。当前会话已完成消息存档，后续可接入真实大模型能力。"

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """按固定大小切分文本用于流式输出。"""
        normalized_text: str = text.strip()
        if normalized_text == "":
            return []

        result: List[str] = []
        start_index: int = 0
        while start_index < len(normalized_text):
            result.append(normalized_text[start_index:start_index + chunk_size])
            start_index = start_index + chunk_size
        return result

    def _resolve_title(self, title: Optional[str]) -> str:
        """计算会话标题。"""
        if title is None:
            return "新对话"

        normalized_title: str = title.strip()
        if normalized_title == "":
            return "新对话"
        return normalized_title
