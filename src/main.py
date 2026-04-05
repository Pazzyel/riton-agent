import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.mysql.aio import AIOMySQLSaver
from modules.knowledgebase.router import knowledgebase_router, rag_chat_router

from config.app_config import app_config
from common.dependencies import (
    blog_vectorize_message_consumer,
    shop_search_agent_service,
    shop_vectorize_message_consumer,
    vectorize_message_consumer,
    voucher_vectorize_message_consumer,
)
from common.exceptions import BusinessException
from modules.session.router import chat_router
from modules.shop_search.router import shop_search_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AIOMySQLSaver.from_conn_string(app_config.DB_URI) as checkpointer:
        await checkpointer.setup()
        shop_search_agent_service.set_checkpointer(checkpointer)
        await vectorize_message_consumer.start()
        await shop_vectorize_message_consumer.start()
        await voucher_vectorize_message_consumer.start()
        await blog_vectorize_message_consumer.start()
        logging.info("LangGraph Checkpointer 已就绪")
        yield

    await blog_vectorize_message_consumer.shutdown()
    await voucher_vectorize_message_consumer.shutdown()
    await shop_vectorize_message_consumer.shutdown()
    await vectorize_message_consumer.shutdown()
    logging.info("LangGraph Checkpointer 连接池已关闭")

app = FastAPI(title="Resume Analysis Service Migration", version="1.0", lifespan=lifespan)

app.include_router(knowledgebase_router.router)
app.include_router(chat_router.router)
app.include_router(shop_search_router.router)

@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    logger.error(f"Business error occurred: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": exc.message,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error occurred: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "Internal Server Error",
            "data": None
        }
    )

origins = [
    # 如果你还有其他前端地址，可以继续往这里加
    "http://localhost:5173",
]



app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8072, reload=True)
