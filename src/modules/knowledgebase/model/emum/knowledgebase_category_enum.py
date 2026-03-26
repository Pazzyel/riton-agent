from enum import Enum


class KnowledgebaseCategoryEnum(str, Enum):
    BLOG = "blog" # 用户发表的评论
    VOUCHER = "voucher" # 店铺团购券消息
    SHOP = "shop" # 商铺信息


