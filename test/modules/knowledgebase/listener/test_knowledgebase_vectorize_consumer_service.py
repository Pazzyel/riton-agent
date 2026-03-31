def test_consumer_routes_by_category_and_fails_invalid(monkeypatch) -> None:
    """Ensure consumer routes by category and fails invalid categories."""
    import asyncio
    from contextlib import asynccontextmanager
    from pathlib import Path
    import sys

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    import types

    fake_repository_module = types.ModuleType("modules.knowledgebase.repository.knowledgebase_repository")
    fake_vector_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_vector_service")
    fake_shop_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_shop_vector_service")
    fake_voucher_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_voucher_vector_service")

    class FakeRepositoryType:
        pass

    class FakeVectorServiceType:
        pass

    fake_repository_module.KnowledgeBaseRepository = FakeRepositoryType
    fake_vector_service_module.KnowledgeBaseVectorService = FakeVectorServiceType
    fake_shop_service_module.KnowledgeBaseShopVectorService = object
    fake_voucher_service_module.KnowledgeBaseVoucherVectorService = object

    monkeypatch.setitem(
        sys.modules,
        "modules.knowledgebase.repository.knowledgebase_repository",
        fake_repository_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "modules.knowledgebase.service.knowledgebase_vector_service",
        fake_vector_service_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "modules.knowledgebase.service.knowledgebase_shop_vector_service",
        fake_shop_service_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "modules.knowledgebase.service.knowledgebase_voucher_vector_service",
        fake_voucher_service_module,
    )

    from modules.knowledgebase.listener import knowledgebase_vectorize_consumer_service as consumer_module
    from modules.knowledgebase.model.emum.knowledgebase_category_enum import KnowledgebaseCategoryEnum
    from modules.knowledgebase.model.entity.knowledgebase_entity import KnowledgeBaseEntity, VectorStatus

    class FakeSession:
        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    @asynccontextmanager
    async def fake_async_session_factory():
        yield FakeSession()

    class FakeRepository:
        def __init__(self, entity_by_id: dict[int, KnowledgeBaseEntity]) -> None:
            self._entity_by_id = entity_by_id
            self.update_calls: list[tuple[int, VectorStatus, str | None]] = []

        async def find_by_id(self, db: FakeSession, kb_id: int):
            _ = db
            return self._entity_by_id.get(kb_id)

        async def update_vector_status(
            self, db: FakeSession, kb_id: int, status: VectorStatus, error: str | None = None
        ) -> None:
            _ = db
            self.update_calls.append((kb_id, status, error))

    class FakeShopVectorService:
        def __init__(self) -> None:
            self.calls: list[tuple[int, str, str]] = []

        async def vectorize_and_store(self, kb_id: int, kb_name: str, content: str) -> None:
            self.calls.append((kb_id, kb_name, content))

    class FakeVoucherVectorService:
        def __init__(self) -> None:
            self.calls: list[tuple[int, str, str]] = []

        async def vectorize_and_store(self, kb_id: int, kb_name: str, content: str) -> None:
            self.calls.append((kb_id, kb_name, content))

    monkeypatch.setattr(consumer_module, "async_session_factory", fake_async_session_factory)

    shop_entity = KnowledgeBaseEntity(id=1, name="Shop KB", category=KnowledgebaseCategoryEnum.SHOP.value)
    voucher_entity = KnowledgeBaseEntity(id=2, name="Voucher KB", category=KnowledgebaseCategoryEnum.VOUCHER.value)
    invalid_entity = KnowledgeBaseEntity(id=3, name="Invalid KB", category=KnowledgebaseCategoryEnum.SHOP.value)

    repository = FakeRepository({1: shop_entity, 2: voucher_entity, 3: invalid_entity})
    shop_service = FakeShopVectorService()
    voucher_service = FakeVoucherVectorService()

    consumer_service = consumer_module.KnowledgeBaseVectorizeConsumerService(
        repository,
        object(),
        shop_service,
        voucher_service,
    )

    asyncio.run(
        consumer_service.process_task(
            kb_id=1,
            content="shop content",
            kb_name=None,
            kb_category=KnowledgebaseCategoryEnum.SHOP.value,
        )
    )

    asyncio.run(
        consumer_service.process_task(
            kb_id=2,
            content="voucher content",
            kb_name=None,
            kb_category=KnowledgebaseCategoryEnum.VOUCHER.value,
        )
    )

    asyncio.run(
        consumer_service.process_task(
            kb_id=3,
            content="invalid content",
            kb_name=None,
            kb_category="invalid",
        )
    )

    assert shop_service.calls == [(1, "Shop KB", "shop content")]
    assert voucher_service.calls == [(2, "Voucher KB", "voucher content")]

    status_by_kb: dict[int, list[VectorStatus]] = {}
    for kb_id, status, _error in repository.update_calls:
        status_by_kb.setdefault(kb_id, []).append(status)

    assert status_by_kb[1] == [VectorStatus.PROCESSING, VectorStatus.COMPLETED]
    assert status_by_kb[2] == [VectorStatus.PROCESSING, VectorStatus.COMPLETED]
    assert status_by_kb[3] == [VectorStatus.PROCESSING, VectorStatus.FAILED]
