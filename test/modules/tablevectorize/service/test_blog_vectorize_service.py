"""Tests for blog vectorize service."""

from datetime import datetime
from pathlib import Path
import sys
from typing import Any, TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from modules.table_vectorize.model.dto.blog_vectorize_dto import BlogVectorizeDto


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio backend only."""
    return "asyncio"


def _prepare_src_import_path() -> None:
    """Ensure src directory is importable for modules.* imports."""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


def _build_blog_dto(operation: str, content: str) -> "BlogVectorizeDto":
    """Build a valid blog dto used by tests."""
    _prepare_src_import_path()
    from modules.table_vectorize.model.dto.blog_vectorize_dto import BlogVectorizeDto

    now: datetime = datetime.now()
    return BlogVectorizeDto(
        operation=operation,
        id=4001,
        shop_id=5001,
        shop_name="山野咖啡",
        x=121.4737,
        y=31.2304,
        h3hex="8a2a1072b59ffff",
        title="周末探店",
        images="http://example.com/blog.jpg",
        content=content,
        liked=88,
        comments=12,
        create_time=now,
        update_time=now,
    )


def test_blog_vector_service_uses_blog_index_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure constructor initializes VectorService with blog index."""
    _prepare_src_import_path()
    from config.app_config import app_config
    from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService

    captured: dict[str, str] = {}

    class FakeVectorService:
        """Lightweight fake vector service for constructor test."""

        def __init__(self, index_url: str) -> None:
            captured["index_url"] = index_url

        async def delete_vector_by_id(self, vector_id: int) -> None:
            return None

        async def add_documents(self, documents: list[object]) -> None:
            return None

    monkeypatch.setattr(
        "modules.table_vectorize.service.blog_vectorize_service.VectorService",
        FakeVectorService,
    )

    BlogVectorizeService()

    assert captured["index_url"] == app_config.blog_index_name


@pytest.mark.anyio
async def test_handle_message_skips_add_for_meaningless_short_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure short meaningless content does not trigger add after cleanup."""
    _prepare_src_import_path()
    from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService

    events: list[tuple[str, object]] = []

    class FakeVectorService:
        """Fake vector service recording call order and payloads."""

        def __init__(self, index_url: str) -> None:
            events.append(("init", index_url))

        async def delete_vector_by_id(self, vector_id: int) -> None:
            events.append(("delete", vector_id))

        async def add_documents(self, documents: list[object]) -> None:
            events.append(("add", documents))

    monkeypatch.setattr(
        "modules.table_vectorize.service.blog_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = BlogVectorizeService()
    dto = _build_blog_dto("UPDATE", "  a\n\t")

    await service.handle_message(dto)

    assert events[1] == ("delete", dto.id)
    assert all(event[0] != "add" for event in events)


@pytest.mark.anyio
async def test_handle_message_chunks_long_content_into_multiple_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure long content is split into multiple chunks and vector documents."""
    _prepare_src_import_path()
    from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService

    events: list[tuple[str, object]] = []

    class FakeVectorService:
        """Fake vector service recording call order and payloads."""

        def __init__(self, index_url: str) -> None:
            events.append(("init", index_url))

        async def delete_vector_by_id(self, vector_id: int) -> None:
            events.append(("delete", vector_id))

        async def add_documents(self, documents: list[object]) -> None:
            events.append(("add", documents))

    monkeypatch.setattr(
        "modules.table_vectorize.service.blog_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = BlogVectorizeService()
    dto = _build_blog_dto("  UpDaTe ", "x" * 1001)

    await service.handle_message(dto)

    assert events[1] == ("delete", dto.id)
    assert events[2][0] == "add"
    docs: list[Any] = events[2][1]
    assert len(docs) >= 2


@pytest.mark.anyio
async def test_handle_message_delete_operation_only_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure delete operation performs delete only without add."""
    _prepare_src_import_path()
    from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService

    events: list[tuple[str, object]] = []

    class FakeVectorService:
        """Fake vector service recording method calls."""

        def __init__(self, index_url: str) -> None:
            events.append(("init", index_url))

        async def delete_vector_by_id(self, vector_id: int) -> None:
            events.append(("delete", vector_id))

        async def add_documents(self, documents: list[object]) -> None:
            events.append(("add", documents))

    monkeypatch.setattr(
        "modules.table_vectorize.service.blog_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = BlogVectorizeService()
    dto = _build_blog_dto("  delete ", "ignored")

    await service.handle_message(dto)

    assert ("delete", dto.id) in events
    assert all(event[0] != "add" for event in events)


@pytest.mark.anyio
async def test_handle_message_sets_enriched_text_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure document content and metadata match required enrichment format."""
    _prepare_src_import_path()
    from modules.table_vectorize.service.blog_vectorize_service import BlogVectorizeService

    events: list[tuple[str, object]] = []

    class FakeVectorService:
        """Fake vector service recording call order and payloads."""

        def __init__(self, index_url: str) -> None:
            events.append(("init", index_url))

        async def delete_vector_by_id(self, vector_id: int) -> None:
            events.append(("delete", vector_id))

        async def add_documents(self, documents: list[object]) -> None:
            events.append(("add", documents))

    monkeypatch.setattr(
        "modules.table_vectorize.service.blog_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = BlogVectorizeService()
    dto = _build_blog_dto("UPDATE", "  好吃，环境不错。  ")

    await service.handle_message(dto)

    docs: list[Any] = events[2][1]
    first_doc = docs[0]
    assert first_doc.page_content == (
        "关于店铺“山野咖啡”的评价：标题：《周末探店》。内容：好吃，环境不错。"
    )
    assert first_doc.metadata["id"] == str(dto.id)
    assert first_doc.metadata["kb_id"] == str(dto.id)
    assert first_doc.metadata["shop_id"] == str(dto.shop_id)
    assert first_doc.metadata["h3hex"] == dto.h3hex
    assert first_doc.metadata["liked"] == dto.liked
    assert first_doc.metadata["comments"] == dto.comments
    assert first_doc.metadata["chunk_index"] == 0

