from typing import Any

from langchain_core.tools import BaseTool

from infrastructure.agent.tool.tool import get_all_tools, get_available_tools

class ShopSearchToolService:
    """商铺推荐工具调用服务。"""

    def __init__(self, tools: list[BaseTool] | None = None) -> None:
        """初始化工具列表。"""
        self._tools: list[BaseTool] | None = tools

    async def get_tools_for_react(self) -> list[BaseTool]:
        """返回供 ToolNode 使用的可调用工具列表，不包含外部工具。"""

        tools: list[BaseTool] = await get_available_tools(include_external=True)
        return tools

    async def get_all_tools_for_react(self) -> list[BaseTool]:
        """返回供 ToolNode 使用的完整工具列表。"""
        # 关键步骤：执行侧工具必须使用完整工具集合，不经过 tool_search 延迟过滤。

        tools: list[BaseTool] = await get_all_tools(include_external=True)
        self._tools = tools
        return tools