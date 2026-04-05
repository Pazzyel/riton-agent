import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.dependencies import shop_search_agent_service
from infrastructure.database.connection import get_async_session
from modules.shop_search.model.dto.shop_search_dto import ShopSearchStreamRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/search", tags=["ShopSearch"])


@router.post("/stream", response_model=None)
async def search_shop_stream(
    request: ShopSearchStreamRequest,
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """流式返回商铺推荐结果。"""
    logger.info("商铺推荐请求到达: query=%s", request.query)
    return StreamingResponse(
        shop_search_agent_service.search_stream(
            db=db,
            query=request.query,
            coordinates=(request.x, request.y),
            user_id=request.user_id,
            session_id=request.session_id,
        ),
        media_type="text/event-stream",
    )
