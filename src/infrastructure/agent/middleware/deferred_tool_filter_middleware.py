from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Sequence

from src.infrastructure.agent.tool.tool_search import get_deferred_registry


@dataclass
class DeferredToolFilterMiddleware:
    """在模型调用前过滤延迟工具 schema 的中间件。"""

    def _filter_tools(self, tools: Sequence[Any]) -> List[Any]:
        """从工具列表中过滤已标记为 deferred 的工具。"""
        # 获取延迟工具名称集合，未设置注册表时直接返回原工具列表副本。
        registry = get_deferred_registry()
        if registry is None:
            return list(tools)

        # 构建延迟工具名集合，并过滤输入工具列表。
        deferred_names: set[str] = {entry.name for entry in registry.entries}
        active_tools: List[Any] = [
            tool_instance
            for tool_instance in tools
            if getattr(tool_instance, "name", None) not in deferred_names
        ]
        return active_tools

    def wrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Any],
    ) -> Any:
        """同步包装模型调用：过滤工具后再调用下游处理器。"""
        # request 不含 tools 字段时透传，避免破坏现有调用链。
        if not hasattr(request, "tools"):
            return handler(request)

        # 过滤 deferred 工具后，尽量使用 override 覆盖请求对象。
        active_tools: List[Any] = self._filter_tools(request.tools)
        if hasattr(request, "override") and callable(request.override):
            return handler(request.override(tools=active_tools))

        # 兜底：无法 override 时直接改写同名属性。
        setattr(request, "tools", active_tools)
        return handler(request)

    async def awrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """异步包装模型调用：过滤工具后再调用下游处理器。"""
        # request 不含 tools 字段时透传，避免破坏现有调用链。
        if not hasattr(request, "tools"):
            return await handler(request)

        # 过滤 deferred 工具后，尽量使用 override 覆盖请求对象。
        active_tools: List[Any] = self._filter_tools(request.tools)
        if hasattr(request, "override") and callable(request.override):
            return await handler(request.override(tools=active_tools))

        # 兜底：无法 override 时直接改写同名属性。
        setattr(request, "tools", active_tools)
        return await handler(request)


def build_deferred_tool_filter_middleware() -> DeferredToolFilterMiddleware:
    """创建延迟工具过滤中间件实例。"""
    # TODO: 在 agent 构建链路中注入该 middleware，拦截模型绑定阶段的工具 schema。
    # TODO: 典型接入点为 create_agent(..., middleware=[...]) 或统一 _build_middlewares(... )。
    return DeferredToolFilterMiddleware()
