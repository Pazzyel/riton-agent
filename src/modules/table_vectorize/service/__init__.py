"""Service helpers for table_vectorize module."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .blog_vectorize_service import BlogVectorizeService
    from .shop_vectorize_service import ShopVectorizeService
    from .voucher_vectorize_service import VoucherVectorizeService


def __getattr__(name: str) -> Any:
    if name == "ShopVectorizeService":
        from .shop_vectorize_service import ShopVectorizeService

        return ShopVectorizeService
    if name == "VoucherVectorizeService":
        from .voucher_vectorize_service import VoucherVectorizeService

        return VoucherVectorizeService
    if name == "BlogVectorizeService":
        from .blog_vectorize_service import BlogVectorizeService

        return BlogVectorizeService

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ShopVectorizeService", "VoucherVectorizeService", "BlogVectorizeService"]
