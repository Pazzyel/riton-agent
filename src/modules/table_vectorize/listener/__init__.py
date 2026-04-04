"""Listener components for table_vectorize module."""

from importlib import import_module
from typing import Any

__all__ = [
    "ShopVectorizeTaskPayload",
    "VoucherVectorizeTaskPayload",
    "BlogVectorizeTaskPayload",
    "ShopVectorizeMessageProducer",
    "VoucherVectorizeMessageProducer",
    "BlogVectorizeMessageProducer",
    "ShopVectorizeMessageConsumer",
    "VoucherVectorizeMessageConsumer",
    "BlogVectorizeMessageConsumer",
]

_EXPORT_MODULE_MAP: dict[str, str] = {
    "ShopVectorizeTaskPayload": ".shop_vectorize_message_producer",
    "ShopVectorizeMessageProducer": ".shop_vectorize_message_producer",
    "VoucherVectorizeTaskPayload": ".voucher_vectorize_message_producer",
    "VoucherVectorizeMessageProducer": ".voucher_vectorize_message_producer",
    "BlogVectorizeTaskPayload": ".blog_vectorize_message_producer",
    "BlogVectorizeMessageProducer": ".blog_vectorize_message_producer",
    "ShopVectorizeMessageConsumer": ".shop_vectorize_message_consumer",
    "VoucherVectorizeMessageConsumer": ".voucher_vectorize_message_consumer",
    "BlogVectorizeMessageConsumer": ".blog_vectorize_message_consumer",
}


def __getattr__(name: str) -> Any:
    """Load listener exports lazily to avoid eager MQ imports."""
    module_name: str | None = _EXPORT_MODULE_MAP.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    return getattr(module, name)
