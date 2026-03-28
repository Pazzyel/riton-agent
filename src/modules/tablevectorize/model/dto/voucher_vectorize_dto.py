from datetime import datetime


class VoucherVectorizeDto(BaseCamelSchema):
    operation: str

    id: int
    shop_id: int
    shop_name: int
    x: float # 商铺经度
    y: float # 商铺维度
    h3hex: str # 地址的h3

    title: str
    description: str # 商品描述，对应表里的sub_title
    rules: str # 使用规则
    pay_value: int
    actual_value: int
    type: int # 0普通/1秒杀
    status: int # 1可用
    create_time: datetime
    update_time: datetime
    daily_limit: int # 每日限购