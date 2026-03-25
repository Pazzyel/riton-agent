from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.session.model.dto.chat_session_dto import SessionListItemDTO
from modules.session.model.orm.chat_session_orm import ChatMessageORM, ChatSessionORM
from modules.session.model.entity.chat_message_entity import ChatMessageEntity, ChatSessionEntity


class ChatSessionRepository:
    """聊天会话仓储层，负责会话与消息的数据访问。"""

    def _to_session_entity(self, orm: ChatSessionORM) -> ChatSessionEntity:
        """将会话 ORM 转换为 Entity。"""
        return ChatSessionEntity(
            r_id=orm.id,
            title=orm.title,
            status=orm.status,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            message_count=orm.message_count,
            is_pinned=bool(orm.is_pinned),
        )

    def _to_message_entity(self, orm: ChatMessageORM) -> ChatMessageEntity:
        """将消息 ORM 转换为 Entity。"""
        return ChatMessageEntity(
            r_id=orm.id,
            session_id=orm.session_id,
            r_type=orm.type,
            content=orm.content,
            message_order=orm.message_order,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            completed=bool(orm.completed),
        )

    async def create_session(self, db: AsyncSession, title: str) -> ChatSessionEntity:
        """创建聊天会话并返回会话实体。"""
        session_data: Dict[str, Any] = {
            "title": title,
            "status": "ACTIVE",
            "message_count": 0,
            "is_pinned": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # SQL: INSERT INTO chat_sessions(title, status, message_count, is_pinned, created_at, updated_at)
        #      VALUES(#{title}, #{status}, #{message_count}, #{is_pinned}, #{created_at}, #{updated_at})
        insert_result = await db.execute(insert(ChatSessionORM).values(**session_data))
        session_id: int = int(insert_result.inserted_primary_key[0])  # type: ignore

        session_entity: Optional[ChatSessionEntity] = await self.get_session_by_id(db, session_id)
        if session_entity is None:
            raise ValueError("Failed to load created session")
        return session_entity

    async def get_session_by_id(self, db: AsyncSession, session_id: int) -> Optional[ChatSessionEntity]:
        """按主键读取单个会话。"""
        stmt = select(ChatSessionORM).where(ChatSessionORM.id == session_id)

        # SQL: SELECT * FROM chat_sessions WHERE id = #{session_id}
        result = await db.execute(stmt)
        session_orm: Optional[ChatSessionORM] = result.scalar_one_or_none()
        if session_orm is None:
            return None
        return self._to_session_entity(session_orm)

    async def list_sessions(self, db: AsyncSession) -> List[SessionListItemDTO]:
        """按置顶和更新时间倒序读取会话列表。"""
        stmt = select(ChatSessionORM).order_by(ChatSessionORM.is_pinned.desc(), ChatSessionORM.updated_at.desc())

        # SQL: SELECT * FROM chat_sessions ORDER BY is_pinned DESC, updated_at DESC
        result = await db.execute(stmt)
        orm_list: List[ChatSessionORM] = list(result.scalars().all())

        response_data: List[SessionListItemDTO] = []
        for orm_item in orm_list:
            mapped_item: SessionListItemDTO = SessionListItemDTO(
                id=orm_item.id,
                title=orm_item.title,
                message_count=orm_item.message_count,
                updated_at=orm_item.updated_at,
                is_pinned=bool(orm_item.is_pinned),
            )
            response_data.append(mapped_item)
        return response_data

    async def get_session_messages(self, db: AsyncSession, session_id: int) -> List[ChatMessageEntity]:
        """按消息序号升序读取会话消息。"""
        stmt = (
            select(ChatMessageORM)
            .where(ChatMessageORM.session_id == session_id)
            .order_by(ChatMessageORM.message_order.asc())
        )

        # SQL: SELECT * FROM chat_messages WHERE session_id = #{session_id} ORDER BY message_order ASC
        result = await db.execute(stmt)
        orm_list: List[ChatMessageORM] = list(result.scalars().all())
        return [self._to_message_entity(item) for item in orm_list]

    async def prepare_stream_messages(self, db: AsyncSession, session_id: int, question: str) -> Optional[int]:
        """写入用户消息并创建 AI 占位消息，返回 AI 消息 ID。"""
        # Step 1: 校验会话存在
        session_stmt = select(ChatSessionORM).where(ChatSessionORM.id == session_id)

        # SQL: SELECT * FROM chat_sessions WHERE id = #{session_id}
        session_result = await db.execute(session_stmt)
        session_orm: Optional[ChatSessionORM] = session_result.scalar_one_or_none()
        if session_orm is None:
            return None

        # Step 2: 写入用户消息与 AI 占位消息
        next_order: int = int(session_orm.message_count)
        now: datetime = datetime.now()
        user_message_data: Dict[str, Any] = {
            "session_id": session_id,
            "type": "USER",
            "content": question,
            "message_order": next_order,
            "completed": True,
            "created_at": now,
            "updated_at": now,
        }
        assistant_message_data: Dict[str, Any] = {
            "session_id": session_id,
            "type": "ASSISTANT",
            "content": "",
            "message_order": next_order + 1,
            "completed": False,
            "created_at": now,
            "updated_at": now,
        }

        # SQL: INSERT INTO chat_messages(session_id, type, content, message_order, completed, created_at, updated_at)
        #      VALUES(#{session_id}, #{type}, #{content}, #{message_order}, #{completed}, #{created_at}, #{updated_at})
        await db.execute(insert(ChatMessageORM).values(**user_message_data))

        # SQL: INSERT INTO chat_messages(session_id, type, content, message_order, completed, created_at, updated_at)
        #      VALUES(#{session_id}, #{type}, #{content}, #{message_order}, #{completed}, #{created_at}, #{updated_at})
        assistant_insert_result = await db.execute(insert(ChatMessageORM).values(**assistant_message_data))
        assistant_message_id: int = int(assistant_insert_result.inserted_primary_key[0])  # type: ignore

        # Step 3: 回写会话消息计数与更新时间
        session_update_data: Dict[str, Any] = {
            "message_count": next_order + 2,
            "updated_at": now,
        }

        # SQL: UPDATE chat_sessions SET message_count = #{message_count}, updated_at = #{updated_at} WHERE id = #{session_id}
        await db.execute(
            update(ChatSessionORM)
            .where(ChatSessionORM.id == session_id)
            .values(**session_update_data)
        )
        return assistant_message_id

    async def complete_stream_message(self, db: AsyncSession, message_id: int, content: str) -> bool:
        """流式回答完成后回写消息内容。"""
        update_data: Dict[str, Any] = {
            "content": content,
            "completed": True,
            "updated_at": datetime.now(),
        }
        stmt = update(ChatMessageORM).where(ChatMessageORM.id == message_id).values(**update_data)

        # SQL: UPDATE chat_messages SET content = #{content}, completed = #{completed}, updated_at = #{updated_at}
        #      WHERE id = #{message_id}
        result = await db.execute(stmt)
        row_count: int = int(result.rowcount or 0)  # type: ignore
        return row_count > 0

    async def update_session_title(self, db: AsyncSession, session_id: int, title: str) -> bool:
        """更新会话标题。"""
        update_data: Dict[str, Any] = {
            "title": title,
            "updated_at": datetime.now(),
        }
        stmt = update(ChatSessionORM).where(ChatSessionORM.id == session_id).values(**update_data)

        # SQL: UPDATE chat_sessions SET title = #{title}, updated_at = #{updated_at} WHERE id = #{session_id}
        result = await db.execute(stmt)
        row_count: int = int(result.rowcount or 0)  # type: ignore
        return row_count > 0

    async def toggle_pin(self, db: AsyncSession, session_id: int) -> Optional[bool]:
        """切换会话置顶状态，并返回切换后的值。"""
        # Step 1: 读取当前置顶状态
        session_stmt = select(ChatSessionORM).where(ChatSessionORM.id == session_id)

        # SQL: SELECT * FROM chat_sessions WHERE id = #{session_id}
        session_result = await db.execute(session_stmt)
        session_orm: Optional[ChatSessionORM] = session_result.scalar_one_or_none()
        if session_orm is None:
            return None

        # Step 2: 写入新的置顶状态
        next_pinned: bool = not bool(session_orm.is_pinned)
        update_data: Dict[str, Any] = {
            "is_pinned": next_pinned,
            "updated_at": datetime.now(),
        }
        stmt = update(ChatSessionORM).where(ChatSessionORM.id == session_id).values(**update_data)

        # SQL: UPDATE chat_sessions SET is_pinned = #{is_pinned}, updated_at = #{updated_at} WHERE id = #{session_id}
        await db.execute(stmt)
        return next_pinned

    async def delete_session(self, db: AsyncSession, session_id: int) -> bool:
        """删除会话及其消息。"""
        # Step 1: 校验会话是否存在
        exists_stmt = select(ChatSessionORM.id).where(ChatSessionORM.id == session_id)

        # SQL: SELECT id FROM chat_sessions WHERE id = #{session_id}
        exists_result = await db.execute(exists_stmt)
        session_exists: Optional[int] = exists_result.scalar_one_or_none()
        if session_exists is None:
            return False

        # Step 2: 先删消息，再删会话
        message_delete_stmt = delete(ChatMessageORM).where(ChatMessageORM.session_id == session_id)
        session_delete_stmt = delete(ChatSessionORM).where(ChatSessionORM.id == session_id)

        # SQL: DELETE FROM chat_messages WHERE session_id = #{session_id}
        await db.execute(message_delete_stmt)

        # SQL: DELETE FROM chat_sessions WHERE id = #{session_id}
        await db.execute(session_delete_stmt)
        return True
