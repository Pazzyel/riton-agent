def test_shop_vector_service_builds_index_url(monkeypatch) -> None:
    """Ensure shop vector service builds a category index URL."""
    from pathlib import Path
    import sys
    import types

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    class FakeSplitter:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    fake_splitter_module = types.ModuleType("langchain_text_splitters")
    fake_splitter_module.RecursiveCharacterTextSplitter = FakeSplitter
    monkeypatch.setitem(sys.modules, "langchain_text_splitters", fake_splitter_module)

    class FakeAiConfig:
        MAX_BATCH_SIZE = 10

    fake_ai_config_module = types.ModuleType("common.ai_config")
    fake_ai_config_module.ai_config = FakeAiConfig()
    monkeypatch.setitem(sys.modules, "common.ai_config", fake_ai_config_module)

    from common.app_config import app_config
    from modules.knowledgebase.service.knowledgebase_shop_vector_service import (
        KnowledgeBaseShopVectorService,
    )
    from infrastructure.vector import vector_service

    captured: dict = {}

    class FakeStore:
        def __init__(self) -> None:
            self.client = object()

    def fake_create_vector_store(index_url: str) -> FakeStore:
        captured["index_url"] = index_url
        return FakeStore()

    monkeypatch.setattr(vector_service, "create_vector_store", fake_create_vector_store)

    service = KnowledgeBaseShopVectorService()

    assert captured["index_url"] == f"{app_config.knowledgebase_index_name}/shop"
    assert service.vector_service._store.__class__ is FakeStore
