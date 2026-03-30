import json
from typing import Iterator, List

import pytest
from langchain_core.tools import BaseTool, tool

from src.infrastructure.agent.tool.tool_search import (
    DeferredToolRegistry,
    reset_deferred_registry,
    set_deferred_registry,
    tool_search,
)


@tool("Read")
def read_tool(file_path: str) -> str:
    """Read a file from disk."""
    return file_path


@tool("Edit")
def edit_tool(file_path: str, content: str) -> str:
    """Edit a file with content."""
    return f"{file_path}:{content}"


@tool("SlackSend")
def slack_send_tool(channel: str, message: str) -> str:
    """Send a message to a Slack channel."""
    return f"{channel}:{message}"


@pytest.fixture(autouse=True)
def clean_deferred_registry() -> Iterator[None]:
    """Ensure test isolation for deferred registry context state."""
    reset_deferred_registry()
    yield
    reset_deferred_registry()


def _build_registry() -> DeferredToolRegistry:
    """Build a registry with reusable test tools."""
    registry: DeferredToolRegistry = DeferredToolRegistry()
    tools: List[BaseTool] = [read_tool, edit_tool, slack_send_tool]
    for tool_instance in tools:
        registry.register(tool_instance)
    return registry


def test_search_select_returns_exact_named_tools() -> None:
    """select 语法应按名称精确匹配工具。"""
    registry: DeferredToolRegistry = _build_registry()

    matched_tools: List[BaseTool] = registry.search("select:Read,Edit")
    matched_names: List[str] = [tool_instance.name for tool_instance in matched_tools]

    assert matched_names == ["Read", "Edit"]


def test_search_plus_query_requires_keyword_in_name() -> None:
    """+keyword 语法应要求工具名包含关键字。"""
    registry: DeferredToolRegistry = _build_registry()

    matched_tools: List[BaseTool] = registry.search("+slack message")
    matched_names: List[str] = [tool_instance.name for tool_instance in matched_tools]

    assert matched_names == ["SlackSend"]


def test_tool_search_returns_json_schema_string() -> None:
    """tool_search 应返回可解析的 JSON 字符串 schema。"""
    registry: DeferredToolRegistry = _build_registry()
    set_deferred_registry(registry)

    search_result: str = tool_search.invoke({"query": "select:Read"})
    parsed_result: List[dict] = json.loads(search_result)

    assert len(parsed_result) == 1
    assert parsed_result[0]["name"] == "Read"
