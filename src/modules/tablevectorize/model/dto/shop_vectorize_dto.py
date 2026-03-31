from datetime import datetime

from infrastructure.model.BaseCamelSchema import BaseCamelSchema


class ShopVectorizeDto(BaseCamelSchema):

    operation: str

    id: int
    name: str # 商铺名称
    type_name: str # 商铺类型分类
    description: str # 商铺描述
    images: str # 图片链接
    area: str # 商圈位置
    address: str # 商铺地址
    x: float # 精度
    y: float # 维度
    h3hex: str # h3哈希值16进制
    avg_price: int # 均价
    sold: int # 销量
    comments: int # 评论数量
    score: int # 评分
    open_hours: str # 营业时间
    create_time: datetime
    update_time: datetime
