import inspect
import json
from typing import Any, AsyncGenerator, Callable, Literal, Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.agent.compact.compact_node_factory import CompactNodeFactory
from infrastructure.agent.compact.message_compact_service import MessageCompactService
from infrastructure.agent.compact.token_estimator import MessageTokenEstimator
from infrastructure.agent.prompt.prompt_service import load_prompt
from modules.session.model.dto.chat_session_dto import CreateSessionRequest
from modules.session.model.entity.chat_message_entity import MessageType
from modules.shop_search.model.entity.shop_search_state import ShopSearchState
from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService
from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService


class PromptProtocol(Protocol):
    """提示词对象协议。"""

    def format_messages(self, **kwargs: Any) -> list[Any]:
        """格式化消息列表。"""


class ModelProtocol(Protocol):
    """聊天模型协议。"""

    async def ainvoke(self, messages: list[Any]) -> Any:
        """异步调用模型。"""


class ShopSearchReactFinalPayload(BaseModel):
    """ReAct 最终输出的结构化结果。"""

    resolved_coordinates: tuple[float, float] = Field(description="最终用于检索的经纬度坐标")
    search_text: str = Field(description="实际用于商铺检索的搜索文本")
    shop_candidates: list[dict[str, Any]] = Field(description="商铺候选列表")
    coupon_map: dict[int, list[dict[str, Any]]] = Field(description="按 shop_id 聚合的优惠券列表")


class ShopSearchParsePayload(BaseModel):
    """意图解析阶段的结构化结果。"""

    keyword: str = Field(description="用户需求关键词")
    category: str = Field(description="商铺类别")
    price_range: str = Field(description="预算偏好")
    explicit_location: str | None = Field(description="用户显式提及的地理位置")


class ShopSearchAgentService:
    """商铺推荐 LangGraph 编排服务。"""

    def __init__(
        self,
        tool_service: ShopSearchToolService,
        rag_service: ShopSearchRagService,
        chat_session_service: Any = None,
        model: ModelProtocol | None = None,
        prompt_loader: Callable[[str], Any] | None = None,
        compact_service: MessageCompactService | None = None,
        token_estimator: MessageTokenEstimator | None = None,
    ) -> None:
        """初始化商铺推荐编排服务。"""
        self.tool_service: ShopSearchToolService = tool_service
        self.rag_service: ShopSearchRagService = rag_service
        self.chat_session_service: Any = chat_session_service
        self._checkpointer: Any | None = None
        self._model: ModelProtocol | None = model
        self._prompt_loader: Callable[[str], Any] | None = prompt_loader
        self.compact_service: MessageCompactService = compact_service or MessageCompactService(
            model=self._get_model(),
            prompt_loader=load_prompt,
        )
        self.token_estimator: MessageTokenEstimator = token_estimator or MessageTokenEstimator()
        self.compact_node_factory: CompactNodeFactory = CompactNodeFactory(
            self.token_estimator,
            self.compact_service,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        """构建 LangGraph。"""
        builder: StateGraph[ShopSearchState] = StateGraph(ShopSearchState)
        builder.add_node("compact_before_parse_node", self.compact_node_factory.build_node("parse_intent_node"))
        builder.add_node("parse_intent_node", self.parse_intent_node)
        builder.add_node("compact_before_react_node", self.compact_node_factory.build_node("react_tool_node"))
        builder.add_node("react_tool_node", self.react_tool_node)
        builder.add_node("retrieve_comment_node", self.retrieve_comment_node)
        builder.add_node("rank_node", self.rank_node)
        builder.add_node("compact_before_generate_node", self.compact_node_factory.build_node("generate_node"))
        builder.add_node("generate_node", self.generate_node)
        builder.add_node("fallback_node", self.fallback_node)
        builder.add_edge(START, "compact_before_parse_node")
        return builder.compile(checkpointer=self._checkpointer)

    def set_checkpointer(self, checkpointer: Any) -> None:
        """设置 checkpointer 并重建 graph。"""
        self._checkpointer = checkpointer
        self.graph = self._build_graph()

    def build_initial_state(
        self,
        query: str,
        coordinates: tuple[float, float],
        user_id: int,
        session_id: int,
        thread_id: str,
    ) -> ShopSearchState:
        """构建图初始状态。"""
        initial_state: ShopSearchState = {
            "origin_query": query,
            "coordinates": coordinates,
            "user_id": user_id,
            "session_id": session_id,
            "thread_id": thread_id,
            "messages": [HumanMessage(content=query)],
            "keyword": "",
            "category": "",
            "price_range": "不限",
            "explicit_location": None,
            "resolved_coordinates": coordinates,
            "search_text": "",
            "shop_candidates": [],
            "coupon_map": {},
            "comment_map": {},
            "score_map": {},
            "ranked_shops": [],
            "final_markdown": "",
            "error_message": None,
        }
        return initial_state

    async def search_stream(
        self,
        db: AsyncSession,
        query: str,
        coordinates: tuple[float, float],
        user_id: int,
        session_id: int | None,
    ) -> AsyncGenerator[str, None]:
        """执行推荐图并输出 SSE 文本流。"""
        normalized_query: str = query.strip()
        resolved_session_id: int = await self._resolve_session_id(db, session_id)
        thread_id: str = str(resolved_session_id)

        await self.chat_session_service.add_session_message(
            db,
            resolved_session_id,
            normalized_query,
            MessageType.USER,
        )

        initial_state: ShopSearchState = self.build_initial_state(
            normalized_query,
            coordinates,
            user_id,
            resolved_session_id,
            thread_id,
        )
        final_text: str
        try:
            final_state: ShopSearchState = await self.graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}},
            )
            final_text = final_state["final_markdown"]
        except Exception as error:
            final_text = f"抱歉，商铺推荐生成失败：{str(error)}"

        await self.chat_session_service.add_session_message(
            db,
            resolved_session_id,
            final_text,
            MessageType.ASSISTANT,
        )

        async for chunk in self._emit_sse(final_text):
            yield chunk

    async def _resolve_session_id(self, db: AsyncSession, session_id: int | None) -> int:
        """解析或创建会话 ID。"""
        if session_id is not None:
            return session_id

        created_session: Any = await self.chat_session_service.create_session(
            db,
            CreateSessionRequest(title="商铺推荐"),
        )
        return int(created_session.id)

    async def parse_intent_node(
        self,
        state: ShopSearchState,
    ) -> Command[Literal["compact_before_react_node", "fallback_node"]]:
        """解析用户意图并决定路由。"""
        try:
            model: ModelProtocol = self._get_model()
            prompt: PromptProtocol = await self._load_prompt("shop_search_parse")
            structured_model: Any = model.with_structured_output(ShopSearchParsePayload)
            parsed: ShopSearchParsePayload = await structured_model.ainvoke(
                prompt.format_messages(
                    messages=state["messages"],
                    query=state["origin_query"],
                )
            )

            keyword: str = parsed.keyword.strip()
            category: str = parsed.category.strip()
            price_range: str = parsed.price_range.strip()
            explicit_location: str | None = parsed.explicit_location
            if explicit_location is not None:
                explicit_location = explicit_location.strip()
                if explicit_location == "":
                    explicit_location = None
            if price_range == "":
                price_range = "不限"

            summary_message: AIMessage = AIMessage(
                content=(
                    f"已解析需求：category={category}, keyword={keyword}, "
                    f"price_range={price_range}, explicit_location={explicit_location or '无'}"
                )
            )

            return Command(
                update={
                    "keyword": keyword,
                    "category": category,
                    "price_range": price_range,
                    "explicit_location": explicit_location,
                    "resolved_coordinates": state["coordinates"],
                    "messages": [summary_message],
                    "error_message": None,
                },
                goto="compact_before_react_node",
            )
        except Exception as error:
            return Command(update={"error_message": str(error)}, goto="fallback_node")

    async def react_tool_node(
        self,
        state: ShopSearchState,
    ) -> Command[Literal["retrieve_comment_node", "fallback_node"]]:
        """通过 ToolNode 进行 ReAct 工具调用循环。"""
        model: ModelProtocol = self._get_model()

        try:
            bound_model: Any = model.bind_tools(await self.tool_service.get_tools_for_react())
            tool_node: ToolNode = ToolNode(await self.tool_service.get_all_tools_for_react())

            system_prompt: str = self._build_tool_react_prompt(state)
            messages: list[Any] = [
                SystemMessage(content=system_prompt),
                *state["messages"],
            ]
            appended_messages: list[Any] = []

            # ReAct 最后的结构化结果。
            final_payload: ShopSearchReactFinalPayload | None = None
            max_steps: int = 15
            step_index: int = 0

            while step_index < max_steps:
                # 获取最新的消息。分析是ToolCall还是最终结果
                ai_message: Any = await bound_model.ainvoke(messages)
                messages.append(ai_message)
                appended_messages.append(ai_message)

                tool_calls: list[Any] = list(getattr(ai_message, "tool_calls", []) or [])
                if len(tool_calls) == 0:
                    structured_model: Any = model.with_structured_output(ShopSearchReactFinalPayload)
                    final_payload = await structured_model.ainvoke(messages[:-1])
                    break

                tool_result: dict[str, Any] = await tool_node.ainvoke({"messages": messages})
                tool_messages: list[Any] = list(tool_result.get("messages", []))
                messages.extend(tool_messages)
                appended_messages.extend(tool_messages)
                step_index += 1

            if final_payload is None:
                return Command(update={"error_message": "工具循环未得到最终结果"}, goto="fallback_node")

            resolved_coordinates: tuple[float, float] = final_payload.resolved_coordinates
            shop_candidates: list[dict[str, Any]] = final_payload.shop_candidates
            coupon_map: dict[int, list[dict[str, Any]]] = final_payload.coupon_map
            search_text: str = final_payload.search_text.strip()
            if search_text == "":
                search_text = state["origin_query"]

            if len(shop_candidates) == 0:
                return Command(
                    update={"error_message": "未检索到商铺", "shop_candidates": [], "search_text": search_text},
                    goto="fallback_node",
                )

            return Command(
                update={
                    "resolved_coordinates": resolved_coordinates,
                    "shop_candidates": shop_candidates,
                    "coupon_map": coupon_map,
                    "search_text": search_text,
                    "messages": appended_messages,
                    "error_message": None,
                },
                goto="retrieve_comment_node",
            )
        except Exception as error:
            return Command(update={"error_message": str(error)}, goto="fallback_node")

    async def retrieve_comment_node(
        self,
        state: ShopSearchState,
    ) -> Command[Literal["rank_node"]]:
        """批量检索候选商铺评论证据。"""
        comment_map: dict[int, list[str]] = {}
        keyword_text: str = state["keyword"] if state["keyword"].strip() != "" else state["origin_query"]
        shop_ids: list[str] = []

        # 关键步骤：评论缺失不阻断主流程，统一降级为空列表。
        shop_item: dict[str, Any]
        for shop_item in state["shop_candidates"]:
            shop_id: int = int(shop_item.get("shop_id", 0))
            if shop_id <= 0:
                continue
            shop_ids.append(str(shop_id))
            try:
                comments: list[str] = await self.rag_service.retrieve_comments(shop_id, keyword_text)
                comment_map[shop_id] = comments
            except Exception:
                comment_map[shop_id] = []

        rag_query_message: AIMessage = AIMessage(
            content=f"调用RAG向量库搜索shops:({','.join(shop_ids)})"
        )
        rag_result_message: ToolMessage = ToolMessage(
            content=json.dumps(comment_map, ensure_ascii=False),
            tool_name="shop_comment_rag",
            tool_call_id="shop_comment_rag",
        )
        return Command(
            update={
                "comment_map": comment_map,
                "messages": [rag_query_message, rag_result_message],
            },
            goto="rank_node",
        )

    async def rank_node(
        self,
        state: ShopSearchState,
    ) -> Command[Literal["compact_before_generate_node", "fallback_node"]]:
        """综合距离评分券匹配评论匹配进行排序。"""
        try:
            ranked: list[dict[str, Any]] = []
            score_map: dict[int, float] = {}

            # 关键步骤：按照统一评分公式生成可解释综合分。
            shop_item: dict[str, Any]
            for shop_item in state["shop_candidates"]:
                shop_id: int = int(shop_item.get("shop_id", 0))
                if shop_id <= 0:
                    continue

                distance_km: float = float(shop_item.get("distance_km", 99.0))
                rating: float = float(shop_item.get("rating", 0.0))
                coupons: list[dict[str, Any]] = state["coupon_map"].get(shop_id, [])
                comments: list[str] = state["comment_map"].get(shop_id, [])

                distance_score: float = max(0.0, min(1.0, 1.0 - distance_km / 10.0))
                rating_score: float = max(0.0, min(1.0, rating / 5.0))
                coupon_score: float = self._calc_coupon_score(coupons, state["price_range"])
                comment_score: float = max(0.0, min(1.0, len(comments) / 5.0))

                final_score: float = (
                    0.35 * distance_score
                    + 0.25 * rating_score
                    + 0.20 * coupon_score
                    + 0.20 * comment_score
                )
                score_map[shop_id] = final_score

                merged_item: dict[str, Any] = dict(shop_item)
                merged_item["score"] = round(final_score, 4)
                merged_item["coupons"] = coupons
                merged_item["comments"] = comments
                ranked.append(merged_item)

            ranked.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
            return Command(update={"score_map": score_map, "ranked_shops": ranked}, goto="compact_before_generate_node")
        except Exception as error:
            return Command(update={"error_message": str(error)}, goto="fallback_node")

    async def generate_node(
        self,
        state: ShopSearchState,
    ) -> Command:
        """生成最终推荐文案。"""
        ranked_payload: str = json.dumps(state["ranked_shops"][:6], ensure_ascii=False)
        try:
            model: ModelProtocol = self._get_model()
            prompt: PromptProtocol = await self._load_prompt("shop_search_generate")
            response: Any = await model.ainvoke(
                prompt.format_messages(
                    messages=state["messages"],
                    query=state["origin_query"],
                    ranked_payload=ranked_payload,
                )
            )
            content_text: str = str(response.content).strip()
            if content_text == "":
                content_text = self._build_fallback_markdown(state)
            return Command(
                update={
                    "final_markdown": content_text,
                    "messages": [AIMessage(content=content_text)],
                },
                goto=END,
            )
        except Exception:
            fallback_text: str = self._build_fallback_markdown(state)
            return Command(
                update={
                    "final_markdown": fallback_text,
                    "messages": [AIMessage(content=fallback_text)],
                },
                goto=END,
            )

    async def fallback_node(
        self,
        state: ShopSearchState,
    ) -> Command:
        """失败兜底节点。"""
        fallback_text: str = self._build_fallback_markdown(state)
        return Command(update={"final_markdown": fallback_text}, goto=END)

    async def _emit_sse(self, content: str) -> AsyncGenerator[str, None]:
        """将完整文本切片并输出 SSE。"""
        text: str = content.strip()
        if text == "":
            text = "抱歉，暂未检索到可推荐的商铺，请换个条件再试试。"

        chunk_size: int = 24
        end_index: int = chunk_size
        while end_index < len(text) + chunk_size:
            part: str = text[:end_index]
            payload: dict[str, str] = {"response": part}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\\n\\n"
            end_index = end_index + chunk_size

        yield "data: [DONE]\\n\\n"

    def _calc_coupon_score(self, coupons: list[dict[str, Any]], price_range: str) -> float:
        """计算优惠券匹配分。"""
        if len(coupons) == 0:
            return 0.0
        max_discount: float = 0.0
        item: dict[str, Any]
        for item in coupons:
            discount_value: float = float(item.get("discount", 0.0))
            if discount_value > max_discount:
                max_discount = discount_value
        discount_score: float = max(0.0, min(1.0, max_discount / 50.0))
        if "不限" in price_range:
            return discount_score
        return max(0.0, min(1.0, discount_score + 0.1))

    def _build_tool_react_prompt(self, state: ShopSearchState) -> str:
        """构建工具 ReAct 执行提示词。"""
        location_text: str = state["explicit_location"] or ""
        return (
            "你是商铺推荐工具调度器。你需要按需调用可用工具，输出最终 JSON。\n"
            "任务目标：\n"
            "1) 如果 explicit_location 非空，先尝试地理解析并得到 resolved_coordinates。\n"
            "2) 用类别+关键词构造 search_text 调用商铺检索，得到 shop_candidates。\n"
            "3) 对每个 shop_id 调用优惠券工具，汇总 coupon_map。\n"
            "4) 最终输出严格 JSON，不要输出其它文本。\n"
            "JSON 字段：resolved_coordinates, search_text, shop_candidates, coupon_map。\n"
            f"当前上下文: keyword={state['keyword']}, category={state['category']}, "
            f"price_range={state['price_range']}, explicit_location={location_text}, "
            f"default_coordinates={state['coordinates']}"
        )

    def _extract_react_final_payload(self, content: str) -> dict[str, Any] | None:
        """从模型输出中提取最终 JSON。"""
        text: str = content.strip()
        if text == "":
            return None
        try:
            parsed: Any = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return None
        except json.JSONDecodeError:
            start: int = text.find("{")
            end: int = text.rfind("}")
            if start == -1 or end == -1 or end < start:
                return None
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None

    def _normalize_coordinates(
        self,
        value: Any,
        fallback: tuple[float, float],
    ) -> tuple[float, float]:
        """标准化坐标值。"""
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return (float(value[0]), float(value[1]))
        if isinstance(value, dict) and "x" in value and "y" in value:
            return (float(value["x"]), float(value["y"]))
        return fallback

    def _normalize_shop_list(self, value: Any) -> list[dict[str, Any]]:
        """标准化商铺列表。"""
        if not isinstance(value, list):
            return []
        result: list[dict[str, Any]] = []
        item: Any
        for item in value:
            if isinstance(item, dict):
                result.append(item)
        return result

    def _normalize_coupon_map(self, value: Any) -> dict[int, list[dict[str, Any]]]:
        """标准化券映射。"""
        if not isinstance(value, dict):
            return {}
        result: dict[int, list[dict[str, Any]]] = {}
        key: Any
        for key in value:
            try:
                shop_id: int = int(key)
            except (ValueError, TypeError):
                continue
            coupon_items: Any = value[key]
            if not isinstance(coupon_items, list):
                result[shop_id] = []
                continue
            normalized_items: list[dict[str, Any]] = []
            item: Any
            for item in coupon_items:
                if isinstance(item, dict):
                    normalized_items.append(item)
            result[shop_id] = normalized_items
        return result

    def _build_fallback_markdown(self, state: ShopSearchState) -> str:
        """构建兜底 Markdown。"""
        top_shops: list[dict[str, Any]] = state["ranked_shops"][:3]
        if len(top_shops) == 0:
            return "抱歉，当前没有找到符合条件的商铺。可以尝试放宽预算或更换地点。"

        lines: list[str] = []
        item: dict[str, Any]
        for item in top_shops:
            shop_id: int = int(item.get("shop_id", 0))
            name: str = str(item.get("name", "未知商铺"))
            distance_km: float = float(item.get("distance_km", 0.0))
            rating: float = float(item.get("rating", 0.0))
            lines.append(f"[[shop_id={shop_id}]]")
            lines.append(f"- {name}：距离约 {distance_km:.1f}km，评分 {rating:.1f}，综合匹配度较高。")
            lines.append("- Tips：建议出发前确认门店营业时间与券使用规则。")
            lines.append("")

        return "\n".join(lines).strip()

    def _get_model(self) -> ModelProtocol:
        """获取模型实例。"""
        if self._model is None:
            # 关键步骤：延迟初始化模型，避免导入阶段读取外部配置。
            from config.ai_config import ai_config
            from langchain_openai import ChatOpenAI

            model: ChatOpenAI = ChatOpenAI(
                model=ai_config.chat_model_name,
                api_key=ai_config.chat_api_key,
                base_url=ai_config.base_url,
                temperature=0,
            )
            self._model = model
        return self._model

    async def _load_prompt(self, node_name: str) -> PromptProtocol:
        """加载提示词模板。"""
        if self._prompt_loader is not None:
            loaded: Any = self._prompt_loader(node_name)
            if inspect.isawaitable(loaded):
                loaded = await loaded
            return loaded

        from infrastructure.agent.prompt.prompt_service import load_prompt

        prompt: Any = await load_prompt(node_name)
        return prompt
