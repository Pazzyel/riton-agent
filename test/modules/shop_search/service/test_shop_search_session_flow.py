import sys
from pathlib import Path
import asyncio

from langchain_core.documents import Document


def _ensure_src_path() -> None:
    """确保测试可导入 src 下一级包。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()


def test_shop_search_request_accepts_optional_session_id() -> None:
    """商铺搜索请求应允许携带可选 session_id。"""
    from modules.shop_search.model.dto.shop_search_dto import ShopSearchStreamRequest

    payload: ShopSearchStreamRequest = ShopSearchStreamRequest(
        query="火锅",
        x=121.47,
        y=31.23,
        user_id=1,
        session_id=99,
    )

    assert payload.session_id == 99


def test_initial_state_contains_session_and_messages() -> None:
    """初始 state 应包含 session/thread 与 messages。"""
    from langchain_core.messages import HumanMessage

    from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
    from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
    from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=ShopSearchToolService(tools=[]),
        rag_service=ShopSearchRagService(_EmptyRetriever()),
        chat_session_service=None,
        model=_NoopModel(),
        prompt_loader=lambda _: _NoopPrompt(),
    )
    state: dict = service.build_initial_state(
        query="火锅",
        coordinates=(121.47, 31.23),
        user_id=1,
        session_id=7,
        thread_id="7",
    )

    assert state["session_id"] == 7
    assert state["thread_id"] == "7"
    assert len(state["messages"]) == 1
    assert isinstance(state["messages"][0], HumanMessage)


def test_search_stream_creates_session_when_missing() -> None:
    """未传 session_id 时应先创建 session 并完成消息落库。"""
    from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
    from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
    from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

    fake_session_service: _FakeChatSessionService = _FakeChatSessionService()
    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=ShopSearchToolService(tools=[]),
        rag_service=ShopSearchRagService(_EmptyRetriever()),
        chat_session_service=fake_session_service,
        model=_NoopModel(),
        prompt_loader=lambda _: _NoopPrompt(),
    )
    service.graph = _FakeGraph("[[shop_id=1001]]\n推荐")

    chunks: list[str] = asyncio.run(
        _collect_chunks(
            service.search_stream(
                db=object(),
                query="火锅",
                coordinates=(121.47, 31.23),
                user_id=1,
                session_id=None,
            )
        )
    )

    assert fake_session_service.created_session_ids == [101]
    assert fake_session_service.added_messages[0] == (101, "火锅", "USER")
    assert fake_session_service.added_messages[-1] == (101, "[[shop_id=1001]]\n推荐", "ASSISTANT")
    assert chunks[-1] == "data: [DONE]\\n\\n"


def test_search_stream_reuses_existing_session_id() -> None:
    """已传 session_id 时不应重复创建会话。"""
    from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
    from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
    from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

    fake_session_service: _FakeChatSessionService = _FakeChatSessionService()
    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=ShopSearchToolService(tools=[]),
        rag_service=ShopSearchRagService(_EmptyRetriever()),
        chat_session_service=fake_session_service,
        model=_NoopModel(),
        prompt_loader=lambda _: _NoopPrompt(),
    )
    service.graph = _FakeGraph("[[shop_id=1002]]\n推荐")

    asyncio.run(
        _drain_async(
            service.search_stream(
                db=object(),
                query="烤肉",
                coordinates=(121.47, 31.23),
                user_id=1,
                session_id=55,
            )
        )
    )

    assert fake_session_service.created_session_ids == []
    assert fake_session_service.added_messages[0][0] == 55


def test_fallback_answer_is_still_persisted() -> None:
    """即使 graph 失败，也应写入 fallback assistant 消息。"""
    from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
    from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
    from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

    fake_session_service: _FakeChatSessionService = _FakeChatSessionService()
    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=ShopSearchToolService(tools=[]),
        rag_service=ShopSearchRagService(_EmptyRetriever()),
        chat_session_service=fake_session_service,
        model=_NoopModel(),
        prompt_loader=lambda _: _NoopPrompt(),
    )
    service.graph = _FailingGraph()

    chunks: list[str] = asyncio.run(
        _collect_chunks(
            service.search_stream(
                db=object(),
                query="异常请求",
                coordinates=(121.47, 31.23),
                user_id=1,
                session_id=55,
            )
        )
    )

    assert fake_session_service.added_messages[-1][0] == 55
    assert fake_session_service.added_messages[-1][2] == "ASSISTANT"
    assert "抱歉" in fake_session_service.added_messages[-1][1]
    assert chunks[-1] == "data: [DONE]\\n\\n"


def test_set_checkpointer_rebuilds_graph() -> None:
    """注入 checkpointer 后应重建 graph。"""
    from langgraph.checkpoint.memory import InMemorySaver

    from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
    from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
    from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=ShopSearchToolService(tools=[]),
        rag_service=ShopSearchRagService(_EmptyRetriever()),
        chat_session_service=_FakeChatSessionService(),
        model=_NoopModel(),
        prompt_loader=lambda _: _NoopPrompt(),
    )
    original_graph: object = service.graph
    fake_checkpointer: InMemorySaver = InMemorySaver()

    service.set_checkpointer(fake_checkpointer)

    assert service._checkpointer is fake_checkpointer
    assert service.graph is not original_graph


def test_search_stream_passes_thread_id_to_graph() -> None:
    """graph 调用应使用 session_id 对应的 thread_id。"""
    from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
    from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
    from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService

    fake_session_service: _FakeChatSessionService = _FakeChatSessionService()
    fake_graph: _FakeGraph = _FakeGraph("[[shop_id=1003]]\n推荐")
    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=ShopSearchToolService(tools=[]),
        rag_service=ShopSearchRagService(_EmptyRetriever()),
        chat_session_service=fake_session_service,
        model=_NoopModel(),
        prompt_loader=lambda _: _NoopPrompt(),
    )
    service.graph = fake_graph

    asyncio.run(
        _drain_async(
            service.search_stream(
                db=object(),
                query="甜品",
                coordinates=(121.47, 31.23),
                user_id=1,
                session_id=55,
            )
        )
    )

    assert fake_graph.last_config == {"configurable": {"thread_id": "55"}}


class _NoopPrompt:
    """空提示词对象。"""

    def format_messages(self, **kwargs: object) -> list[tuple[str, str]]:
        """返回固定消息列表。"""
        _ = kwargs
        return [("user", "noop")]


class _NoopModel:
    """空模型。"""

    async def ainvoke(self, messages: list[tuple[str, str]]) -> object:
        """不应被调用。"""
        _ = messages
        raise AssertionError("_NoopModel should not be called")


class _EmptyRetriever:
    """空评论检索器。"""

    async def retrieve(
        self,
        query: str,
        top_k: int,
        filters: list[dict] | None = None,
    ) -> list[Document]:
        _ = query
        _ = top_k
        _ = filters
        return []


class _FakeSessionDTO:
    """测试用会话 DTO。"""

    def __init__(self, session_id: int) -> None:
        """初始化会话 ID。"""
        self.id: int = session_id


class _FakeChatSessionService:
    """测试用会话服务。"""

    def __init__(self) -> None:
        """初始化记录列表。"""
        self.created_session_ids: list[int] = []
        self.added_messages: list[tuple[int, str, str]] = []

    async def create_session(self, db: object, request: object) -> _FakeSessionDTO:
        """返回固定创建结果。"""
        _ = db
        _ = request
        self.created_session_ids.append(101)
        return _FakeSessionDTO(101)

    async def add_session_message(self, db: object, session_id: int, message: str, message_type: object) -> int:
        """记录写入的消息。"""
        _ = db
        type_text: str = getattr(message_type, "value", str(message_type))
        self.added_messages.append((session_id, message, str(type_text)))
        return len(self.added_messages)


class _FakeGraph:
    """测试用 graph。"""

    def __init__(self, final_markdown: str) -> None:
        """初始化最终返回内容。"""
        self.final_markdown: str = final_markdown
        self.last_config: object | None = None

    async def ainvoke(self, state: dict, config: object | None = None) -> dict:
        """返回带最终文案的状态。"""
        self.last_config = config
        updated_state: dict = dict(state)
        updated_state["final_markdown"] = self.final_markdown
        return updated_state


class _FailingGraph:
    """测试用失败 graph。"""

    async def ainvoke(self, state: dict, config: object | None = None) -> dict:
        """抛出异常模拟 graph 执行失败。"""
        _ = state
        _ = config
        raise RuntimeError("graph failed")


async def _collect_chunks(generator: object) -> list[str]:
    """收集异步流输出。"""
    items: list[str] = []
    async for item in generator:
        items.append(item)
    return items


async def _drain_async(generator: object) -> None:
    """消费异步生成器。"""
    async for _ in generator:
        pass
