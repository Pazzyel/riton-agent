def test_dependencies_wire_new_vector_services(monkeypatch) -> None:
    """Ensure dependency wiring uses category vector services and new query/delete APIs."""
    from pathlib import Path
    import sys
    import types

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[2]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    captured: dict[str, object] = {}

    def _capture_call(target: str, args: tuple[object, ...]) -> None:
        captured[target] = args

    if "common" in sys.modules:
        monkeypatch.delitem(sys.modules, "common", raising=False)
    monkeypatch.delitem(sys.modules, "common.dependencies", raising=False)

    fake_file_document_module = types.ModuleType("infrastructure.file.document_parse_service")
    fake_file_hash_module = types.ModuleType("infrastructure.file.file_hash_service")
    fake_file_storage_module = types.ModuleType("infrastructure.file.file_storage_service")
    fake_file_validation_module = types.ModuleType("infrastructure.file.file_validation_service")

    class _EmptyService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

    fake_file_document_module.DocumentParseService = _EmptyService
    fake_file_hash_module.FileHashService = _EmptyService
    fake_file_storage_module.FileStorageService = _EmptyService
    fake_file_validation_module.FileValidationService = _EmptyService

    monkeypatch.setitem(sys.modules, "infrastructure.file.document_parse_service", fake_file_document_module)
    monkeypatch.setitem(sys.modules, "infrastructure.file.file_hash_service", fake_file_hash_module)
    monkeypatch.setitem(sys.modules, "infrastructure.file.file_storage_service", fake_file_storage_module)
    monkeypatch.setitem(sys.modules, "infrastructure.file.file_validation_service", fake_file_validation_module)

    fake_vector_service_module = types.ModuleType("infrastructure.vector.vector_service")

    class FakeVectorService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

    fake_vector_service_module.VectorService = FakeVectorService
    monkeypatch.setitem(sys.modules, "infrastructure.vector.vector_service", fake_vector_service_module)

    fake_kb_listener_module = types.ModuleType("modules.knowledgebase.listener")

    class FakeKnowledgeBaseVectorizeConsumerService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs
            _capture_call("vectorize_consumer", args)

    fake_kb_listener_module.KnowledgeBaseVectorizeConsumerService = FakeKnowledgeBaseVectorizeConsumerService
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.listener", fake_kb_listener_module)

    fake_consumer_module = types.ModuleType("modules.knowledgebase.listener.vectorize_message_consumer")
    fake_producer_module = types.ModuleType("modules.knowledgebase.listener.vectorize_message_producer")

    class FakeVectorizeMessageConsumer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs
            _capture_call("vectorize_message_consumer", args)

    class FakeVectorizeMessageProducer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    fake_consumer_module.VectorizeMessageConsumer = FakeVectorizeMessageConsumer
    fake_producer_module.VectorizeMessageProducer = FakeVectorizeMessageProducer
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.listener.vectorize_message_consumer", fake_consumer_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.listener.vectorize_message_producer", fake_producer_module)

    fake_repository_module = types.ModuleType("modules.knowledgebase.repository")

    class FakeKnowledgeBaseRepository:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

    fake_repository_module.KnowledgeBaseRepository = FakeKnowledgeBaseRepository
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.repository", fake_repository_module)

    fake_kb_service_module = types.ModuleType("modules.knowledgebase")

    class FakeKnowledgeBaseListService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeKnowledgeBaseParseService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeKnowledgeBasePersistenceService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs


    fake_kb_service_module.KnowledgeBaseListService = FakeKnowledgeBaseListService
    fake_kb_service_module.KnowledgeBaseParseService = FakeKnowledgeBaseParseService
    fake_kb_service_module.KnowledgeBasePersistenceService = FakeKnowledgeBasePersistenceService
    class FakeKnowledgeBaseVectorService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    fake_kb_service_module.KnowledgeBaseVectorService = FakeKnowledgeBaseVectorService
    monkeypatch.setitem(sys.modules, "modules.knowledgebase", fake_kb_service_module)

    fake_count_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_count_service")
    fake_delete_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_delete_service")
    fake_query_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_query_service")
    fake_upload_service_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_upload_service")
    fake_shop_vector_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_shop_vector_service")
    fake_voucher_vector_module = types.ModuleType("modules.knowledgebase.service.knowledgebase_voucher_vector_service")

    class FakeKnowledgeBaseCountService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeKnowledgeBaseDeleteService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs
            _capture_call("delete_service", args)

    class FakeKnowledgeBaseQueryService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs
            _capture_call("query_service", args)

    class FakeKnowledgeBaseUploadService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeKnowledgeBaseShopVectorService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeKnowledgeBaseVoucherVectorService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    fake_count_service_module.KnowledgeBaseCountService = FakeKnowledgeBaseCountService
    fake_delete_service_module.KnowledgeBaseDeleteService = FakeKnowledgeBaseDeleteService
    fake_query_service_module.KnowledgeBaseQueryService = FakeKnowledgeBaseQueryService
    fake_upload_service_module.KnowledgeBaseUploadService = FakeKnowledgeBaseUploadService
    fake_shop_vector_module.KnowledgeBaseShopVectorService = FakeKnowledgeBaseShopVectorService
    fake_voucher_vector_module.KnowledgeBaseVoucherVectorService = FakeKnowledgeBaseVoucherVectorService
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.service.knowledgebase_count_service", fake_count_service_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.service.knowledgebase_delete_service", fake_delete_service_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.service.knowledgebase_query_service", fake_query_service_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.service.knowledgebase_upload_service", fake_upload_service_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.service.knowledgebase_shop_vector_service", fake_shop_vector_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.service.knowledgebase_voucher_vector_service", fake_voucher_vector_module)

    fake_session_repo_module = types.ModuleType("modules.session.repository.chat_session_repository")
    fake_session_service_module = types.ModuleType("modules.session.service.chat_session_service")

    class FakeChatSessionRepository:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeChatSessionService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeRagChatRepository:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    class FakeRagChatSessionService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = kwargs

    fake_session_repo_module.ChatSessionRepository = FakeChatSessionRepository
    fake_session_service_module.ChatSessionService = FakeChatSessionService
    monkeypatch.setitem(sys.modules, "modules.session.repository.chat_session_repository", fake_session_repo_module)
    monkeypatch.setitem(sys.modules, "modules.session.service.chat_session_service", fake_session_service_module)

    import importlib.util

    dependencies_path = src_root / "common" / "dependencies.py"
    spec = importlib.util.spec_from_file_location("common.dependencies", dependencies_path)
    assert spec is not None
    dependencies = importlib.util.module_from_spec(spec)
    dependencies.rag_chat_repository = FakeRagChatRepository()
    sys.modules["common.dependencies"] = dependencies
    assert spec.loader is not None
    spec.loader.exec_module(dependencies)

    vectorize_args = captured.get("vectorize_consumer")
    assert vectorize_args is not None
    assert len(vectorize_args) == 4
    assert isinstance(vectorize_args[2], FakeKnowledgeBaseShopVectorService)
    assert isinstance(vectorize_args[3], FakeKnowledgeBaseVoucherVectorService)

    delete_args = captured.get("delete_service")
    assert delete_args is not None
    assert len(delete_args) == 4
    assert isinstance(delete_args[1], FakeKnowledgeBaseShopVectorService)
    assert isinstance(delete_args[2], FakeKnowledgeBaseVoucherVectorService)

    query_args = captured.get("query_service")
    assert query_args is not None
    assert len(query_args) == 2
    assert isinstance(query_args[0], FakeKnowledgeBaseShopVectorService)
    assert isinstance(query_args[1], FakeKnowledgeBaseVoucherVectorService)
