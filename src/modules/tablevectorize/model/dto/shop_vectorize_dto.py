from datetime import datetime

from infrastructure.model.BaseCamelSchema import BaseCamelSchema


class ShopVectorizeDto(BaseCamelSchema):

    operation: str

    id: int
    name: str
    type_name: str # 商铺类型分类
    images: str
    area: str
    address: str
    x: float
    y: float
    h3hex: str
    avg_price: int
    sold: int
    comments: int # 评论数量
    score: int
    open_hours: str
    create_time: datetime
    update_time: datetime
