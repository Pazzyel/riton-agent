import asyncio
import sys
from pathlib import Path

def _ensure_src_path() -> None:
    """确保测试可以导入 src 下模块。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_text: str = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)


_ensure_src_path()

from modules.shop_search.service.shop_search_tool_service import ShopSearchToolService


class DummyTool:
    """用于测试的假工具。"""

    def __init__(self, name: str) -> None:
        """初始化假工具。"""
        self.name: str = name
        self.description: str = name

    async def ainvoke(self, params: dict[str, object]) -> dict[str, object]:
        """异步返回入参。"""
        await asyncio.sleep(0)
        return {"tool": self.name, "params": params}

