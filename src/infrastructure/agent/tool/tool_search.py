import contextvars
import json
import re
from dataclasses import dataclass
from typing import List

from langchain_core.tools import BaseTool, tool
from langchain_core.utils.function_calling import convert_to_openai_function

MAX_RESULTS: int = 5


@dataclass
class DeferredToolEntry:
    """延迟加载工具的轻量元数据。"""

    name: str
    description: str
    tool: BaseTool


class DeferredToolRegistry:
    """延迟工具注册表，支持按查询语法检索工具。"""

    def __init__(self) -> None:
        """初始化空注册表。"""
        self._entries: List[DeferredToolEntry] = []

    def register(self, tool_instance: BaseTool) -> None:
        """注册一个延迟工具。"""
        self._entries.append(
            DeferredToolEntry(
                name=tool_instance.name,
                description=tool_instance.description or "",
                tool=tool_instance,
            )
        )

    def search(self, query: str) -> List[BaseTool]:
        """根据查询语法在注册表中搜索工具。"""
        # 处理 select:name1,name2 语法，进行精确名称匹配。
        if query.startswith("select:"):
            names: set[str] = {name.strip() for name in query[7:].split(",") if name.strip()}
            return [entry.tool for entry in self._entries if entry.name in names][:MAX_RESULTS]

        # 处理 +keyword rest 语法，先约束名称，再按剩余条件排序。
        if query.startswith("+"):
            parts: List[str] = query[1:].split(None, 1)
            if len(parts) == 0 or parts[0] == "":
                return []

            required: str = parts[0].lower()
            candidates: List[DeferredToolEntry] = [
                entry for entry in self._entries if required in entry.name.lower()
            ]
            if len(parts) > 1:
                rest_query: str = parts[1]
                candidates.sort(
                    key=lambda entry: _regex_score(rest_query, entry),
                    reverse=True,
                )
            return [entry.tool for entry in candidates][:MAX_RESULTS]

        # 默认语法：将 query 视为正则，匹配 name + description。
        try:
            regex: re.Pattern[str] = re.compile(query, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(query), re.IGNORECASE)

        scored_entries: List[tuple[int, DeferredToolEntry]] = []
        for entry in self._entries:
            searchable_text: str = f"{entry.name} {entry.description}"
            if regex.search(searchable_text):
                score: int = 2 if regex.search(entry.name) else 1
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: item[0], reverse=True)
        return [entry.tool for _, entry in scored_entries][:MAX_RESULTS]

    @property
    def entries(self) -> List[DeferredToolEntry]:
        """返回当前注册条目的副本。"""
        return list(self._entries)

    def __len__(self) -> int:
        """返回当前注册表中的工具数量。"""
        return len(self._entries)


_registry_var: contextvars.ContextVar[DeferredToolRegistry | None] = contextvars.ContextVar(
    "deferred_tool_registry",
    default=None,
)


def set_deferred_registry(registry: DeferredToolRegistry) -> None:
    """设置当前上下文的延迟工具注册表。"""
    _registry_var.set(registry)


def get_deferred_registry() -> DeferredToolRegistry | None:
    """获取当前上下文的延迟工具注册表。"""
    return _registry_var.get()


def reset_deferred_registry() -> None:
    """重置当前上下文中的延迟工具注册表。"""
    _registry_var.set(None)


def get_deferred_tools_prompt_section() -> str:
    """生成系统提示词中的延迟工具名称区块。"""
    # 当前项目尚未接入全局 tool_search 配置，先按“有注册表即展示”处理。
    registry: DeferredToolRegistry | None = get_deferred_registry()
    if registry is None or len(registry.entries) == 0:
        return ""

    names: str = "\n".join(entry.name for entry in registry.entries)
    return f"<available-deferred-tools>\n{names}\n</available-deferred-tools>"


def _regex_score(query: str, entry: DeferredToolEntry) -> int:
    """统计查询在名称与描述中的正则命中次数。"""
    # 编译查询正则，非法正则自动降级为字面量匹配。
    try:
        regex: re.Pattern[str] = re.compile(query, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(query), re.IGNORECASE)

    # 统计 name + description 的命中次数，作为排序分数。
    searchable_text: str = f"{entry.name} {entry.description}"
    matches: List[str] = regex.findall(searchable_text)
    return len(matches)


@tool
def tool_search(query: str) -> str:
    """Fetch full schema definitions for deferred tools so the model can call them.

    Deferred tools are only exposed to the model by name in the
    ``<available-deferred-tools>`` prompt block. Before fetching schema from
    this tool, those deferred tools are not directly callable because the model
    does not know their argument definitions.

    Query syntax (exactly three forms):

    1) ``select:name1,name2``
       - Exact name selection (no fuzzy match).
       - Example: ``select:Read,Edit,Grep``

    2) ``+keyword rest``
       - Required filter: tool name must contain ``keyword``.
       - Ranking: matched candidates are sorted by relevance of ``rest``.
       - Example: ``+slack send message``

    3) ``keyword-or-regex``
       - General regex search over ``tool_name + tool_description``.
       - If regex is invalid, the query is treated as escaped literal text.
       - Name matches rank above description-only matches.
       - Example: ``notebook jupyter``

    Args:
        query: Search expression used to locate deferred tools.

    Returns:
        A JSON string (OpenAI function schema array) for matched tools.
        Maximum result count is 5. If no registry exists, returns
        ``"No deferred tools available."``. If no match exists, returns
        ``"No tools found matching: {query}"``.
    """
    # 获取延迟注册表，若不存在直接返回提示信息。
    registry: DeferredToolRegistry | None = get_deferred_registry()
    if registry is None:
        return "No deferred tools available."

    # 搜索匹配工具，若无结果返回提示信息。
    matched_tools: List[BaseTool] = registry.search(query)
    if len(matched_tools) == 0:
        return f"No tools found matching: {query}"

    # 将工具序列化为 OpenAI function schema，并输出 JSON 字符串。
    try:
        tool_defs: List[Dict[str, Any]] = [
            convert_to_openai_function(tool_instance)
            for tool_instance in matched_tools[:MAX_RESULTS]
        ]
        return json.dumps(tool_defs, indent=2, ensure_ascii=False)
    except Exception as exc:
        return f"Failed to serialize matched tools: {exc}"
