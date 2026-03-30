from dataclasses import dataclass
from typing import Iterator, List

import pytest
from langchain_core.tools import BaseTool, tool

from src.infrastructure.agent.middleware.deferred_tool_filter_middleware import (
    DeferredToolFilterMiddleware,
)
from src.infrastructure.agent.tool.tool_search import (
    DeferredToolRegistry,
    reset_deferred_registry,
    set_deferred_registry,
)


@tool("Read")
def read_tool(file_path: str) -> str:
    """Read a file from disk."""
    return file_path


@tool("Edit")
def edit_tool(file_path: str, content: str) -> str:
    """Edit a file from disk."""
    return f"{file_path}:{content}"


@dataclass
class FakeModelRequest:
    """Simple request object for middleware unit tests."""

    tools: List[BaseTool]

    def override(self, tools: List[BaseTool]) -> "FakeModelRequest":
        """Return a new request with replaced tools list."""
        return FakeModelRequest(tools=tools)


@pytest.fixture(autouse=True)
def clean_deferred_registry() -> Iterator[None]:
    """Ensure deferred registry is reset around each test."""
    reset_deferred_registry()
    yield
    reset_deferred_registry()


def test_filter_tools_removes_deferred_tools() -> None:
    """过滤逻辑应移除 registry 中的 deferred 工具。"""
    registry: DeferredToolRegistry = DeferredToolRegistry()
    registry.register(read_tool)
    set_deferred_registry(registry)

    middleware: DeferredToolFilterMiddleware = DeferredToolFilterMiddleware()
    filtered_tools: List[BaseTool] = middleware._filter_tools([read_tool, edit_tool])
    filtered_names: List[str] = [tool_instance.name for tool_instance in filtered_tools]

    assert filtered_names == ["Edit"]


def test_wrap_model_call_uses_override_for_filtered_request() -> None:
    """wrap_model_call 应通过 override 传递过滤后的工具列表。"""
    registry: DeferredToolRegistry = DeferredToolRegistry()
    registry.register(read_tool)
    set_deferred_registry(registry)

    middleware: DeferredToolFilterMiddleware = DeferredToolFilterMiddleware()
    request: FakeModelRequest = FakeModelRequest(tools=[read_tool, edit_tool])

    def handler(filtered_request: FakeModelRequest) -> List[str]:
        """Return tool names for assertion."""
        return [tool_instance.name for tool_instance in filtered_request.tools]

    handled_names: List[str] = middleware.wrap_model_call(request=request, handler=handler)
    assert handled_names == ["Edit"]
