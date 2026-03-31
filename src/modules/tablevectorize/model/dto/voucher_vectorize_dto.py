from datetime import datetime


class VoucherVectorizeDto(BaseCamelSchema):
    operation: str

    id: int
    shop_id: int # 商铺id
    shop_name: int # 商铺名称
    x: float # 商铺经度
    y: float # 商铺维度
    h3hex: str # 地址的h3

    title: str # 团购券标题
    description: str # 团购券描述，对应表里的sub_title
    rules: str # 使用规则
    pay_value: int # 支付价格（优惠后）
    actual_value: int # 原价
    type: int # 0普通/1秒杀
    status: int # 1可用 0下架
    create_time: datetime
    update_time: datetime
    daily_limit: int # 每日限购