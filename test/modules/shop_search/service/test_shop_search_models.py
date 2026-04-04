import sys
from pathlib import Path


def _ensure_src_path() -> None:
    """确保测试可导入 src 下一级包。"""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_src_path()


def test_shop_search_state_and_dto_importable() -> None:
    """验证商铺搜索 DTO 与状态模型可导入。"""
    from modules.shop_search.model.dto.shop_search_dto import ShopSearchStreamRequest
    from modules.shop_search.model.entity.shop_search_state import ShopSearchState

    assert ShopSearchStreamRequest is not None
    assert ShopSearchState is not None
