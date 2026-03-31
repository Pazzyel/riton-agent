def test_vector_store_uses_full_index_url(monkeypatch) -> None:
    """Ensure vector store accepts full index URL."""
    from pathlib import Path
    import sys
    from _pytest.monkeypatch import MonkeyPatch

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    from common.ai_config import ai_config
    from common.app_config import app_config
    from infrastructure.vector import vector_store

    class FakeStore:
        def __init__(self, es_url: str, index_name: str, embedding: object, strategy: object) -> None:
            self.es_url = es_url
            self.index_name = index_name
            self.embedding = embedding
            self.strategy = strategy

    class FakeStrategy:
        pass

    assert isinstance(monkeypatch, MonkeyPatch)
    dummy_embedding: object = object()
    index_url: str = "vector/full/index"

    monkeypatch.setattr(vector_store, "AsyncElasticsearchStore", FakeStore)
    monkeypatch.setattr(vector_store, "AsyncDenseVectorStrategy", FakeStrategy)
    monkeypatch.setattr(ai_config, "category_embedding", dummy_embedding, raising=False)

    store = vector_store.create_vector_store(index_url)

    assert store.es_url == app_config.elasticsearch_url
    assert store.index_name == index_url
    assert store.embedding is dummy_embedding


def test_get_vector_index_name_normalizes_slashes() -> None:
    """Ensure index name joins prefix and category safely."""
    from pathlib import Path
    import sys

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    from infrastructure.vector import vector_store

    assert vector_store.get_vector_index_name("vector/", "/blog") == "vector/blog"


def test_create_vector_store_with_category_uses_index_builder(monkeypatch) -> None:
    """Ensure prefix/category API delegates to create_vector_store."""
    from pathlib import Path
    import sys

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    from infrastructure.vector import vector_store

    captured: dict = {}

    def fake_create_vector_store(index_url: str) -> str:
        captured["index_url"] = index_url
        return "store"

    monkeypatch.setattr(vector_store, "create_vector_store", fake_create_vector_store)

    store = vector_store.create_vector_store_with_category("vector", "blog")

    assert store == "store"
    assert captured["index_url"] == "vector/blog"
