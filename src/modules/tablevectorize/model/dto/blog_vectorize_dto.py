from datetime import datetime

from infrastructure.model.BaseCamelSchema import BaseCamelSchema


class BlogVectorizeDto(BaseCamelSchema):
    operation: str

    id: int
    shop_id: int
    x: float
    y: float
    h3hex: str

    title: str
    images: str
    content: str
    liked: int
    comments: int
    create_time: datetime
    update_time: datetime