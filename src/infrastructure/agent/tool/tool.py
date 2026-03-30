from typing import List

from langchain_core.tools import BaseTool

from src.infrastructure.agent.tool.tool_search import (
    DeferredToolRegistry,
    reset_deferred_registry,
    set_deferred_registry,
    tool_search,
)


def is_tool_search_enabled() -> bool:
    """判断是否启用工具渐进式加载能力。"""
    # TODO: 从应用配置读取 tool_search.enabled 开关。
    return True


def _load_builtin_tools(
    model_name: str | None = None,
    groups: List[str] | None = None,
    subagent_enabled: bool = False,
) -> List[BaseTool]:
    """加载当前可直接暴露的内置工具。"""
    # TODO: 按 model_name、groups、subagent_enabled 加载真实内置工具。
    # 当前项目尚未接入具体内置工具实现，先返回空列表。
    _ = model_name
    _ = groups
    _ = subagent_enabled
    return []


def _load_external_tools(
    model_name: str | None = None,
    groups: List[str] | None = None,
) -> List[BaseTool]:
    """加载外部工具（例如 MCP / 三方工具服务）。"""
    # TODO: 从外部工具配置读取已启用工具源（例如 MCP server 列表）。
    # TODO: 拉取外部工具缓存或实时工具定义，并转换为 BaseTool。
    # TODO: 按 model_name 与 groups 过滤外部工具可见性。
    _ = model_name
    _ = groups
    return []


def get_available_tools(
    model_name: str | None = None,
    groups: List[str] | None = None,
    include_external: bool = True,
    subagent_enabled: bool = False,
) -> List[BaseTool]:
    """获取可用工具列表，并支持外部工具的渐进式加载。"""
    # 每次构建工具列表前重置延迟注册表，避免上下文污染。
    reset_deferred_registry()

    # 加载内置工具，这些工具默认直接暴露给模型。
    builtin_tools: List[BaseTool] = _load_builtin_tools(
        model_name=model_name,
        groups=groups,
        subagent_enabled=subagent_enabled,
    )

    # 根据参数决定是否加载外部工具。
    external_tools: List[BaseTool] = []
    if include_external:
        external_tools = _load_external_tools(model_name=model_name, groups=groups)

    # 未启用渐进式加载时，内置工具和外部工具都直接返回。
    if not is_tool_search_enabled():
        return builtin_tools + external_tools

    # 启用渐进式加载时，将外部工具注册到 deferred registry。
    registry: DeferredToolRegistry = DeferredToolRegistry()
    for external_tool in external_tools:
        registry.register(external_tool)
    set_deferred_registry(registry)

    # 将 tool_search 暴露给模型，用于按需拉取延迟工具 schema。
    return builtin_tools + [tool_search]
