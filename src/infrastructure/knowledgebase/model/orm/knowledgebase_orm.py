from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models import Base


class KnowledgeBaseORM(Base):
    __tablename__ = 'knowledge_bases'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=True)
    storage_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    access_count: Mapped[int] = mapped_column(Integer, default=1)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_status: Mapped[VectorStatus] = mapped_column(
        SQLEnum(VectorStatus, name="vector_status", create_type=False),
        default=VectorStatus.PENDING
    )
    vector_error: Mapped[str] = mapped_column(String(500), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # 如果为文件上传，该字段为空，否则为文本对应的表的id
    table_id: Mapped[int] = mapped_column(Integer,nullable=True)