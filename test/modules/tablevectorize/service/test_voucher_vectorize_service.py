"""Tests for voucher vectorize service."""

from datetime import datetime
from pathlib import Path
import sys
from typing import Any, TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from modules.tablevectorize.model.dto.voucher_vectorize_dto import VoucherVectorizeDto


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


def _build_voucher_dto(operation: str) -> "VoucherVectorizeDto":
    """Build a valid voucher dto used by tests."""
    _prepare_src_import_path()
    from modules.tablevectorize.model.dto.voucher_vectorize_dto import VoucherVectorizeDto

    now: datetime = datetime.now()
    return VoucherVectorizeDto(
        operation=operation,
        id=2001,
        shop_id=3001,
        shop_name="老街烧烤",
        x=121.4737,
        y=31.2304,
        h3hex="8a2a1072b59ffff",
        title="双人烧烤套餐",
        description="含牛羊肉拼盘和饮品",
        rules="仅限堂食，节假日不可用",
        pay_value=128,
        actual_value=188,
        type=0,
        status=1,
        create_time=now,
        update_time=now,
        daily_limit=50,
    )


def test_voucher_vector_service_uses_voucher_index_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure constructor initializes VectorService with voucher index."""
    _prepare_src_import_path()
    from config.app_config import app_config
    from modules.tablevectorize.service.voucher_vectorize_service import VoucherVectorizeService

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
        "modules.tablevectorize.service.voucher_vectorize_service.VectorService",
        FakeVectorService,
    )

    VoucherVectorizeService()

    assert captured["index_url"] == app_config.voucher_index_name


@pytest.mark.anyio
async def test_handle_message_updates_with_delete_before_add(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure non-delete operation deletes old vector first then adds one document."""
    _prepare_src_import_path()
    from modules.tablevectorize.service.voucher_vectorize_service import VoucherVectorizeService

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
        "modules.tablevectorize.service.voucher_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = VoucherVectorizeService()
    dto = _build_voucher_dto("  UpDaTe ")

    await service.handle_message(dto)

    assert events[1] == ("delete", dto.id)
    assert events[2][0] == "add"

    docs: list[Any] = events[2][1]
    assert len(docs) == 1

    document = docs[0]
    assert (
        document.page_content
        == "商铺“老街烧烤”有团购券可以购买：名称双人烧烤套餐。描述：含牛羊肉拼盘和饮品。适用规则：仅限堂食，节假日不可用。"
    )
    assert isinstance(document.metadata["id"], str)
    assert isinstance(document.metadata["shop_id"], str)
    assert document.metadata["id"] == str(dto.id)
    assert document.metadata["kb_id"] == str(dto.id)
    assert document.metadata["shop_id"] == str(dto.shop_id)
    assert document.metadata["status"] == dto.status
    assert document.metadata["h3hex"] == dto.h3hex


@pytest.mark.anyio
async def test_handle_message_delete_operation_only_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure delete operation performs delete only without add."""
    _prepare_src_import_path()
    from modules.tablevectorize.service.voucher_vectorize_service import VoucherVectorizeService

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
        "modules.tablevectorize.service.voucher_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = VoucherVectorizeService()
    dto = _build_voucher_dto("  DELETE ")

    await service.handle_message(dto)

    assert ("delete", dto.id) in events
    assert all(event[0] != "add" for event in events)


@pytest.mark.anyio
async def test_handle_message_unknown_operation_still_uses_upsert_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure unknown non-delete operation still executes delete then add flow."""
    _prepare_src_import_path()
    from modules.tablevectorize.service.voucher_vectorize_service import VoucherVectorizeService

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
        "modules.tablevectorize.service.voucher_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = VoucherVectorizeService()
    dto = _build_voucher_dto("  ARCHIVE ")

    await service.handle_message(dto)

    assert events[1] == ("delete", dto.id)
    assert events[2][0] == "add"
    assert len(events[2][1]) == 1


@pytest.mark.anyio
async def test_handle_message_add_documents_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure downstream add failure bubbles up to caller."""
    _prepare_src_import_path()
    from modules.tablevectorize.service.voucher_vectorize_service import VoucherVectorizeService

    events: list[tuple[str, object]] = []

    class FakeVectorService:
        """Fake vector service raising on add."""

        def __init__(self, index_url: str) -> None:
            events.append(("init", index_url))

        async def delete_vector_by_id(self, vector_id: int) -> None:
            events.append(("delete", vector_id))

        async def add_documents(self, documents: list[object]) -> None:
            events.append(("add", documents))
            raise RuntimeError("add failed")

    monkeypatch.setattr(
        "modules.tablevectorize.service.voucher_vectorize_service.VectorService",
        FakeVectorService,
    )

    service = VoucherVectorizeService()
    dto = _build_voucher_dto("UPDATE")

    with pytest.raises(RuntimeError, match="add failed"):
        await service.handle_message(dto)

    assert events[1] == ("delete", dto.id)
    assert events[2][0] == "add"
