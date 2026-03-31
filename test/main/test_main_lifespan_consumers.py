import importlib.util
import sys
import types
from pathlib import Path


def test_lifespan_starts_and_shuts_down_all_consumers(monkeypatch) -> None:
    """Ensure app lifespan starts and shuts down all vectorize consumers."""

    class FakeConsumer:
        def __init__(self, name: str) -> None:
            self.name: str = name
            self.start_calls: int = 0
            self.shutdown_calls: int = 0

        async def start(self) -> None:
            self.start_calls += 1

        async def shutdown(self) -> None:
            self.shutdown_calls += 1

    class FakeFastAPI:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

        def include_router(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

        def exception_handler(self, *args: object, **kwargs: object):
            _ = args
            _ = kwargs

            def _decorator(func):
                return func

            return _decorator

        def add_middleware(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

    class FakeJSONResponse:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

    class FakeCheckpointer:
        async def setup(self) -> None:
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            _ = exc_type
            _ = exc
            _ = tb

    class FakeAIOMySQLSaver:
        @staticmethod
        def from_conn_string(_db_uri: str) -> FakeCheckpointer:
            return FakeCheckpointer()

    class FakeAppConfig:
        DB_URI: str = "mysql://fake"

    class FakeBusinessException(Exception):
        code: int = 400
        message: str = "error"

    fake_fastapi_module = types.ModuleType("fastapi")
    fake_fastapi_module.FastAPI = FakeFastAPI
    fake_fastapi_module.Request = object

    fake_cors_module = types.ModuleType("fastapi.middleware.cors")
    fake_cors_module.CORSMiddleware = object

    fake_responses_module = types.ModuleType("fastapi.responses")
    fake_responses_module.JSONResponse = FakeJSONResponse

    fake_aio_module = types.ModuleType("langgraph.checkpoint.mysql.aio")
    fake_aio_module.AIOMySQLSaver = FakeAIOMySQLSaver

    fake_kb_router_module = types.ModuleType("modules.knowledgebase.router")
    fake_kb_router_module.knowledgebase_router = types.SimpleNamespace(router=object())
    fake_kb_router_module.rag_chat_router = types.SimpleNamespace(router=object())

    fake_chat_router_module = types.ModuleType("modules.session.router")
    fake_chat_router_module.chat_router = types.SimpleNamespace(router=object())

    knowledgebase_consumer = FakeConsumer("knowledgebase")
    shop_consumer = FakeConsumer("shop")
    voucher_consumer = FakeConsumer("voucher")
    blog_consumer = FakeConsumer("blog")

    fake_dependencies_module = types.ModuleType("common.dependencies")
    fake_dependencies_module.knowledgebase_query_service = object()
    fake_dependencies_module.vectorize_message_consumer = knowledgebase_consumer
    fake_dependencies_module.shop_vectorize_message_consumer = shop_consumer
    fake_dependencies_module.voucher_vectorize_message_consumer = voucher_consumer
    fake_dependencies_module.blog_vectorize_message_consumer = blog_consumer

    fake_app_config_module = types.ModuleType("common.app_config")
    fake_app_config_module.app_config = FakeAppConfig()

    fake_exceptions_module = types.ModuleType("common.exceptions")
    fake_exceptions_module.BusinessException = FakeBusinessException

    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi_module)
    monkeypatch.setitem(sys.modules, "fastapi.middleware.cors", fake_cors_module)
    monkeypatch.setitem(sys.modules, "fastapi.responses", fake_responses_module)
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.mysql.aio", fake_aio_module)
    monkeypatch.setitem(sys.modules, "modules.knowledgebase.router", fake_kb_router_module)
    monkeypatch.setitem(sys.modules, "modules.session.router", fake_chat_router_module)
    monkeypatch.setitem(sys.modules, "common.dependencies", fake_dependencies_module)
    monkeypatch.setitem(sys.modules, "common.app_config", fake_app_config_module)
    monkeypatch.setitem(sys.modules, "common.exceptions", fake_exceptions_module)

    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[2]
    main_path: Path = project_root / "src" / "main.py"
    spec = importlib.util.spec_from_file_location("main", main_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    async def _run_lifespan() -> None:
        async with module.lifespan(module.app):
            assert knowledgebase_consumer.start_calls == 1
            assert shop_consumer.start_calls == 1
            assert voucher_consumer.start_calls == 1
            assert blog_consumer.start_calls == 1
            assert knowledgebase_consumer.shutdown_calls == 0
            assert shop_consumer.shutdown_calls == 0
            assert voucher_consumer.shutdown_calls == 0
            assert blog_consumer.shutdown_calls == 0

    import asyncio

    asyncio.run(_run_lifespan())

    assert knowledgebase_consumer.shutdown_calls == 1
    assert shop_consumer.shutdown_calls == 1
    assert voucher_consumer.shutdown_calls == 1
    assert blog_consumer.shutdown_calls == 1
