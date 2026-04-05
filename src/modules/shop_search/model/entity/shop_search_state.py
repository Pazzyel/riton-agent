from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ShopSearchState(TypedDict):
    """商铺推荐图执行状态。"""

    origin_query: str
    coordinates: tuple[float, float]
    user_id: int
    session_id: int
    thread_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    keyword: str
    category: str
    price_range: str
    explicit_location: str | None
    resolved_coordinates: tuple[float, float]
    search_text: str
    shop_candidates: list[dict[str, Any]]
    coupon_map: dict[int, list[dict[str, Any]]]
    comment_map: dict[int, list[str]]
    score_map: dict[int, float]
    ranked_shops: list[dict[str, Any]]
    final_markdown: str
    error_message: str | None
