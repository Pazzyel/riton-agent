from pydantic import Field

from infrastructure.model.BaseCamelSchema import BaseCamelSchema


class ShopSearchStreamRequest(BaseCamelSchema):
    """商铺推荐流式查询请求参数。"""

    query: str = Field(..., min_length=1)
    x: float
    y: float
    user_id: int
