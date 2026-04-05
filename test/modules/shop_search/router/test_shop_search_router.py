import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _ensure_src_path() -> None:
    """确保测试可以导入 src 下模块。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()

def test_shop_search_stream_route_exists() -> None:
    """商铺搜索流式接口应存在。"""
    class FakeShopSearchAgentService:
        """测试用商铺推荐服务。"""

        def __init__(self) -> None:
            """记录透传参数。"""
            self.calls: list[dict[str, object]] = []

        async def search_stream(
            self,
            db: object,
            query: str,
            coordinates: tuple[float, float],
            user_id: int,
            session_id: int | None,
        ):
            """返回最小 SSE 响应。"""
            self.calls.append(
                {
                    "db": db,
                    "query": query,
                    "coordinates": coordinates,
                    "user_id": user_id,
                    "session_id": session_id,
                }
            )
            yield "data: {\"response\":\"ok\"}\\n\\n"
            yield "data: [DONE]\\n\\n"

    fake_shop_search_service: FakeShopSearchAgentService = FakeShopSearchAgentService()
    fake_dependencies_module = types.ModuleType("common.dependencies")
    fake_dependencies_module.shop_search_agent_service = fake_shop_search_service
    sys.modules["common.dependencies"] = fake_dependencies_module

    fake_db_connection_module = types.ModuleType("infrastructure.database.connection")

    async def fake_get_async_session():
        """返回固定 db 对象。"""
        yield object()

    fake_db_connection_module.get_async_session = fake_get_async_session
    sys.modules["infrastructure.database.connection"] = fake_db_connection_module

    from modules.shop_search.router import shop_search_router

    app: FastAPI = FastAPI()
    app.include_router(shop_search_router.router)
    client: TestClient = TestClient(app)
    response = client.post(
        "/ai/search/stream",
        json={"query": "火锅", "x": 121.47, "y": 31.23, "user_id": 1, "session_id": 88},
    )
    assert response.status_code in [200, 422]
    assert fake_shop_search_service.calls[-1]["session_id"] == 88
