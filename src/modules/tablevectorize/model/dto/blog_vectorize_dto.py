from datetime import datetime

from infrastructure.model.BaseCamelSchema import BaseCamelSchema


class BlogVectorizeDto(BaseCamelSchema):
    operation: str

    id: int
    shop_id: int # 商铺id
    shop_name: str # 商铺名称
    x: float # 商铺经度
    y: float # 商铺纬度
    h3hex: str # 商铺h3

    title: str # 贴文标题
    images: str # 贴文图片链接
    content: str # 贴文内容
    liked: int # 点赞数目
    comments: int # 评论数目
    create_time: datetime
    update_time: datetime