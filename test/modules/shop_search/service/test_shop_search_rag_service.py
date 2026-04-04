import asyncio
import sys
from datetime import datetime, timedelta
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

from modules.shop_search.service.shop_search_rag_service import ShopSearchRagService


class DummyBlogVectorService:
    """用于测试的评论向量服务。"""

    async def retrieve_by_shop(
        self,
        shop_id: int,
        keyword: str,
        top_k: int,
    ) -> list[dict[str, str]]:
        """返回包含新旧评论的混合数据。"""
        _ = shop_id
        _ = keyword
        _ = top_k
        now: datetime = datetime.now()
        old_time: datetime = now - timedelta(days=500)
        return [
            {
                "content": "生日布置很用心",
                "create_time": now.isoformat(),
            },
            {
                "content": "很久以前的评论",
                "create_time": old_time.isoformat(),
            },
        ]


def test_retrieve_comments_filters_old_records() -> None:
    """应仅保留一年内评论。"""
    service: ShopSearchRagService = ShopSearchRagService(DummyBlogVectorService())
    comments: list[str] = asyncio.run(service.retrieve_comments(1001, "生日"))
    assert comments == ["生日布置很用心"]
