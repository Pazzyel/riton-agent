import asyncio
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _ensure_src_path() -> None:
    """确保测试可以导入 src 下模块。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()


@tool("external_demo")
def external_demo_tool() -> str:
    """测试用外部工具。"""
    return "ok"


def test_get_available_tools_loads_external_tools_when_tool_search_disabled(monkeypatch) -> None:
    """未启用 tool_search 时应直接返回外部工具而不是 coroutine。"""
    from infrastructure.agent.tool import tool as tool_module

    monkeypatch.setattr(tool_module.ai_config, "enable_tool_search", False)

    async def fake_load_external_tools(**kwargs: Any) -> list[Any]:
        """返回固定外部工具列表。"""
        _ = kwargs
        return [external_demo_tool]

    monkeypatch.setattr(tool_module, "_load_external_tools", fake_load_external_tools)

    tools: list[Any] = asyncio.run(tool_module.get_available_tools(include_external=True))

    assert len(tools) == 1
    assert tools[0].name == "external_demo"
