def test_vector_service_single_store_index_specific(monkeypatch) -> None:
    """Ensure vector service uses the provided index URL."""
    from pathlib import Path
    import sys

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[3]
    src_root: Path = project_root / "src"
    sys.path.insert(0, str(src_root))

    from infrastructure.vector import vector_service

    captured: dict = {}

    class FakeStore:
        def __init__(self) -> None:
            self.client = object()

    def fake_create_vector_store(index_url: str) -> FakeStore:
        captured["index_url"] = index_url
        return FakeStore()

    monkeypatch.setattr(vector_service, "create_vector_store", fake_create_vector_store)

    index_url = "vector/index"
    service = vector_service.VectorService(index_url)

    assert captured["index_url"] == index_url
    assert service._store.__class__ is FakeStore
