"""Tests for shop vectorize service."""

from datetime import datetime
from pathlib import Path
import sys
from typing import Any, TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from modules.tablevectorize.model.dto.shop_vectorize_dto import ShopVectorizeDto


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


def _build_shop_dto(operation: str) -> "ShopVectorizeDto":
    """Build a valid shop dto used by tests."""
    _prepare_src_import_path()
    from modules.tablevectorize.model.dto.shop_vectorize_dto import ShopVectorizeDto

    now: datetime = datetime.now()
    return ShopVectorizeDto(
        operation=operation,
        id=1001,
        name="老王面馆",
        type_name="面馆",
        description="手工面",
        images="http://example.com/a.jpg",
        area="静安寺",
        address="南京西路100号",
        x=121.4737,
        y=31.2304,
        h3hex="8a2a1072b59ffff",
        avg_price=32,
        sold=200,
        comments=66,
        score=48,
        open_hours="10:00-22:00",
        create_time=now,
        update_time=now,
    )


def test_shop_vector_service_uses_shop_index_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure constructor initializes VectorService with shop index."""
    _prepare_src_import_path()
    from config.app_config import app_config
    from modules.tablevectorize.service.shop_vectorize_service import ShopVectorizeService

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
        "modules.tablevectorize.service.shop_vectorize_service.VectorService",
        FakeVectorService,
    )

    ShopVectorizeService()

    assert captured["index_url"] == app_config.shop_index_name


@pytest.mark.anyio
async def test_handle_message_updates_with_delete_before_add(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure non-delete operation deletes old vector first then adds document."""
    _prepare_src_import_path()
    from modules.tablevectorize.service.shop_vectorize_service import ShopVectorizeService

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
        "modules.tablevectorize.service.shop_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = ShopVectorizeService()
    dto = _build_shop_dto("  UpDaTe ")

    await service.handle_message(dto)

    assert events[1] == ("delete", dto.id)
    assert events[2][0] == "add"

    docs: list[Any] = events[2][1]
    assert len(docs) == 1

    document = docs[0]
    assert document.page_content == "老王面馆是一家位于静安寺商圈，地址在南京西路100号的面馆店。"
    assert document.metadata["id"] == str(dto.id)
    assert document.metadata["type_name"] == dto.type_name
    assert document.metadata["h3hex"] == dto.h3hex


@pytest.mark.anyio
async def test_handle_message_delete_operation_only_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure delete operation performs delete only without add."""
    _prepare_src_import_path()
    from modules.tablevectorize.service.shop_vectorize_service import ShopVectorizeService

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
        "modules.tablevectorize.service.shop_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = ShopVectorizeService()
    dto = _build_shop_dto("  DELETE ")

    await service.handle_message(dto)

    assert ("delete", dto.id) in events
    assert all(event[0] != "add" for event in events)
