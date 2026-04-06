import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage


def _ensure_src_path() -> None:
    """确保测试可导入 src 下一级包。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_src_path()

from modules.shop_search.service.shop_search_agent_service import ShopSearchAgentService
from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService


class FakeTool:
    """测试用异步工具。"""

    def __init__(self, name: str, response: dict[str, Any]) -> None:
        """初始化工具和返回内容。"""
        self.name: str = name
        self.description: str = name
        self._response: dict[str, Any] = response

    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        """返回预置响应。"""
        _ = payload
        await asyncio.sleep(0)
        return self._response


class FakePrompt:
    """测试用提示词对象。"""

    def __init__(self, template_name: str) -> None:
        """初始化提示词对象。"""
        self.template_name: str = template_name

    def format_messages(self, **kwargs: Any) -> list[tuple[str, str]]:
        """格式化消息。"""
        if self.template_name == "shop_search_parse":
            return [("user", f"parse::{kwargs.get('query', '')}")]
        return [("user", f"generate::{kwargs.get('ranked_payload', '')}")]


class _RecordingPrompt:
    """用于记录 format_messages 入参的测试 prompt。"""

    def __init__(self, template_name: str) -> None:
        self.template_name: str = template_name
        self.last_kwargs: dict[str, Any] = {}

    def format_messages(self, **kwargs: Any) -> list[tuple[str, str]]:
        self.last_kwargs = kwargs
        if self.template_name == "shop_search_parse":
            return [("user", f"parse::{kwargs.get('query', '')}")]
        return [("user", f"generate::{kwargs.get('ranked_payload', '')}")]


class FakeModel:
    """测试用模型。"""

    def __init__(self) -> None:
        """初始化测试模型状态。"""
        self.structured_schema: Any = None

    def with_structured_output(self, schema: Any) -> "FakeStructuredModel":
        """返回带结构化输出能力的测试模型。"""
        self.structured_schema = schema
        return FakeStructuredModel(schema)

    def bind_tools(self, tools: list[Any]) -> "FakeModel":
        """绑定工具后返回自身。"""
        _ = tools
        return self

    async def ainvoke(self, messages: list[tuple[str, str]]) -> AIMessage:
        """根据提示类型返回固定内容。"""
        last_message: Any = messages[-1]
        text: str
        if isinstance(last_message, tuple):
            text = str(last_message[1])
        else:
            text = str(getattr(last_message, "content", ""))
        await asyncio.sleep(0)
        if text.startswith("parse::"):
            query_text: str = text.split("::", 1)[1]
            if "静安" in query_text:
                return AIMessage(
                    content='{"keyword":"环境好","category":"火锅","price_range":"200以内","explicit_location":"静安区"}'
                )
            return AIMessage(
                content='{"keyword":"安静","category":"咖啡","price_range":"不限","explicit_location":null}'
            )
        if text.startswith("generate::"):
            return AIMessage(
                content="[[shop_id=1001]]\n推荐理由：距离近、评价高、优惠合适、评论提到生日氛围好。"
            )
        if "静安" in text:
            return AIMessage(
                content=json.dumps(
                    {
                        "resolved_coordinates": [121.41, 31.22],
                        "search_text": "火锅 环境好",
                        "shop_candidates": [
                            {"shop_id": 1001, "distance_km": 1.2, "rating": 4.8, "name": "静安火锅馆"},
                            {"shop_id": 1002, "distance_km": 3.1, "rating": 4.6, "name": "生日火锅屋"},
                            {"shop_id": 1003, "distance_km": 0.9, "rating": 4.4, "name": "安静小馆"},
                        ],
                        "coupon_map": {
                            "1001": [{"discount": 25, "max_price": 200}],
                            "1002": [{"discount": 25, "max_price": 200}],
                            "1003": [{"discount": 25, "max_price": 200}],
                        },
                    },
                    ensure_ascii=False,
                )
            )
        return AIMessage(
            content="[[shop_id=1001]]\n推荐理由：距离近、评价高、优惠合适、评论提到生日氛围好。"
        )


class FakeBlogRetriever:
    """测试用评论检索器。"""

    async def retrieve_by_shop(
        self,
        shop_id: int,
        keyword: str,
        top_k: int,
    ) -> list[dict[str, str]]:
        """返回一年内评论。"""
        _ = top_k
        return [
            {
                "content": f"店铺{shop_id}评论命中{keyword}",
                "create_time": "2026-01-01T00:00:00",
            }
        ]


class FakeStructuredModel:
    """测试用结构化输出模型。"""

    def __init__(self, schema: Any) -> None:
        """记录 schema。"""
        self.schema: Any = schema

    async def ainvoke(self, messages: list[Any]) -> Any:
        """返回结构化对象。"""
        text: str = str(messages[-1][1]) if isinstance(messages[-1], tuple) else str(getattr(messages[-1], "content", ""))
        await asyncio.sleep(0)
        if "parse::" in text:
            return self.schema(
                keyword="环境好",
                category="火锅",
                price_range="200以内",
                explicit_location="静安区",
            )
        return self.schema(
            resolved_coordinates=(121.41, 31.22),
            search_text="火锅 环境好",
            shop_candidates=[
                {"shop_id": 1001, "distance_km": 1.2, "rating": 4.8, "name": "静安火锅馆"},
                {"shop_id": 1002, "distance_km": 3.1, "rating": 4.6, "name": "生日火锅屋"},
            ],
            coupon_map={
                1001: [{"discount": 25, "max_price": 200}],
                1002: [{"discount": 25, "max_price": 200}],
            },
        )


def _build_service() -> ShopSearchAgentService:
    """构建用于测试的 agent service。"""
    tool_service: ShopSearchToolService = ShopSearchToolService(
        tools=[
            FakeTool("maps_geo", {"x": 121.41, "y": 31.22}),
            FakeTool(
                "shop_search",
                {
                    "shops": [
                        {"shop_id": 1001, "distance_km": 1.2, "rating": 4.8, "name": "静安火锅馆"},
                        {"shop_id": 1002, "distance_km": 3.1, "rating": 4.6, "name": "生日火锅屋"},
                        {"shop_id": 1003, "distance_km": 0.9, "rating": 4.4, "name": "安静小馆"},
                    ]
                },
            ),
            FakeTool(
                "coupon_query",
                {"coupons": [{"discount": 25, "max_price": 200}]},
            ),
        ]
    )
    rag_service: ShopSearchRagService = ShopSearchRagService(FakeBlogRetriever())
    service: ShopSearchAgentService = ShopSearchAgentService(
        tool_service=tool_service,
        rag_service=rag_service,
        model=FakeModel(),
        prompt_loader=lambda node_name: FakePrompt(node_name),
    )
    service.tool_service.get_tools_for_react = _fake_get_empty_tools  # type: ignore[method-assign]
    service.tool_service.get_all_tools_for_react = _fake_get_empty_tools  # type: ignore[method-assign]
    return service


def test_parse_routes_to_geo_when_explicit_location_present() -> None:
    """解析完成后应进入工具 ReAct 节点。"""
    service: ShopSearchAgentService = _build_service()
    state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    command: Any = asyncio.run(service.parse_intent_node(state))
    assert service._model.structured_schema is not None
    assert command.update["messages"][-1].type == "ai"
    assert command.goto == "compact_before_react_node"


def test_stream_output_contains_done_marker() -> None:
    """SSE 输出应包含 DONE 结束标记。"""
    service: ShopSearchAgentService = _build_service()
    chunks: list[str] = asyncio.run(_collect_chunks(service._emit_sse("[[shop_id=1]]\n测试推荐")))
    assert chunks[-1] == "data: [DONE]\\n\\n"


def test_graph_with_explicit_location_runs_geo_branch() -> None:
    """完整图执行时显式位置应触发坐标替换。"""
    service: ShopSearchAgentService = _build_service()
    initial_state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    final_state: dict[str, Any] = asyncio.run(service.graph.ainvoke(initial_state))
    assert final_state["resolved_coordinates"] != initial_state["coordinates"]
    assert final_state["final_markdown"].startswith("[[shop_id=")


def test_react_tool_node_uses_structured_output_schema() -> None:
    """ReAct 最终结果应通过结构化输出约束字段名称。"""
    service: ShopSearchAgentService = _build_service()
    state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    parsed_command: Any = asyncio.run(service.parse_intent_node(state))
    next_state: dict[str, Any] = {**state, **parsed_command.update}

    command: Any = asyncio.run(service.react_tool_node(next_state))

    assert service._model.structured_schema is not None
    assert command.update["resolved_coordinates"] == (121.41, 31.22)
    assert command.update["search_text"] == "火锅 环境好"
    assert len(command.update["messages"]) >= 1
    assert command.update["messages"][-1].type == "ai"


def test_messages_reducer_appends_instead_of_overwriting() -> None:
    """messages 应使用 reducer 聚合，而不是被后续节点覆盖。"""
    service: ShopSearchAgentService = _build_service()
    initial_state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    final_state: dict[str, Any] = asyncio.run(service.graph.ainvoke(initial_state))

    assert len(final_state["messages"]) >= 4


def test_service_builds_compact_services() -> None:
    """推荐 agent service 应初始化压缩相关服务。"""
    service: ShopSearchAgentService = _build_service()

    assert service.compact_service is not None
    assert service.token_estimator is not None


def test_compact_before_parse_node_uses_factory_output() -> None:
    """parse 前压缩节点应通过工厂生成并正常工作。"""
    service: ShopSearchAgentService = _build_service()
    assert service.compact_node_factory is not None


def test_compact_before_parse_node_can_compact_messages_when_threshold_reached() -> None:
    """达到阈值时工厂生成的压缩节点应返回压缩更新。"""
    service: ShopSearchAgentService = _build_service()
    service.token_estimator = _ForcedCompactEstimator()
    service.compact_node_factory = service.compact_node_factory.__class__(service.token_estimator, service.compact_service)
    state: dict[str, Any] = service.build_initial_state("火锅", (121.47, 31.23), 1, 7, "7")
    state["messages"] = _build_large_message_history()

    compact_node = service.compact_node_factory.build_node("parse_intent_node")
    command: Any = compact_node(state)

    assert any("会话摘要" in str(message.content) for message in command.update["messages"])


def test_parse_intent_uses_messages_from_state() -> None:
    """parse 节点应直接使用 state 中的 messages 渲染 prompt。"""
    service: ShopSearchAgentService = _build_service()
    recording_prompt: _RecordingPrompt = _RecordingPrompt("shop_search_parse")
    service._prompt_loader = lambda _: recording_prompt
    state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    state["messages"] = [AIMessage(content="compacted-history")]

    _ = asyncio.run(service.parse_intent_node(state))

    assert recording_prompt.last_kwargs["messages"][0].content == "compacted-history"


def test_parse_intent_passes_compacted_messages_to_prompt_placeholder() -> None:
    """parse 节点应将压缩后的 messages 通过 prompt 的 messages 变量传入。"""
    service: ShopSearchAgentService = _build_service()
    recording_prompt: _RecordingPrompt = _RecordingPrompt("shop_search_parse")
    service._prompt_loader = lambda _: recording_prompt
    state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    state["messages"] = [AIMessage(content="compacted-history")]

    asyncio.run(service.parse_intent_node(state))

    assert recording_prompt.last_kwargs["messages"][0].content == "compacted-history"


def test_generate_node_uses_compacted_messages() -> None:
    """generate 节点应使用 state 中已压缩的 messages。"""
    service: ShopSearchAgentService = _build_service()
    recording_prompt: _RecordingPrompt = _RecordingPrompt("shop_search_generate")
    service._prompt_loader = lambda _: recording_prompt
    state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    state["messages"] = [AIMessage(content="compacted-history")]
    state["ranked_shops"] = [{"shop_id": 1001, "name": "静安火锅馆", "score": 0.95}]

    command: Any = asyncio.run(service.generate_node(state))

    assert command.goto == "__end__"
    assert recording_prompt.last_kwargs["messages"][0].content == "compacted-history"


def test_retrieve_comment_node_appends_rag_ai_and_tool_messages() -> None:
    """RAG 检索阶段应补 AIMessage 与 ToolMessage。"""
    service: ShopSearchAgentService = _build_service()
    state: dict[str, Any] = service.build_initial_state("静安区附近火锅", (121.47, 31.23), 1, 7, "7")
    state["keyword"] = "环境好"
    state["shop_candidates"] = [
        {"shop_id": 1001, "distance_km": 1.2, "rating": 4.8, "name": "静安火锅馆"},
        {"shop_id": 1002, "distance_km": 3.1, "rating": 4.6, "name": "生日火锅屋"},
    ]

    command: Any = asyncio.run(service.retrieve_comment_node(state))

    assert command.update["messages"][-2].type == "ai"
    assert command.update["messages"][-1].type == "tool"


async def _collect_chunks(generator: Any) -> list[str]:
    """收集异步生成器输出。"""
    result: list[str] = []
    async for item in generator:
        result.append(item)
    return result


async def _fake_get_empty_tools() -> list[Any]:
    """返回空工具列表，避免 ToolNode 依赖真实工具对象。"""
    return []


class _ForcedCompactEstimator:
    """强制触发压缩的测试估算器。"""

    def estimate_messages_tokens(self, messages: list[Any]) -> int:
        """返回固定高 token 数。"""
        _ = messages
        return 200000

    def should_compact(self, token_count: int) -> bool:
        """始终触发压缩。"""
        _ = token_count
        return True


def _build_large_message_history() -> list[Any]:
    """构造较长的历史消息列表。"""
    history: list[Any] = []
    index: int
    for index in range(8):
        history.append(_human_message(f"用户历史消息{index}" * 30))
        history.append(AIMessage(content=f"助手历史消息{index}" * 30))
    return history


def _human_message(content: str) -> Any:
    """构造用户消息。"""
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=content)
