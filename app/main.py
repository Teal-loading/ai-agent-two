"""FastAPI 应用入口。

启动：``uvicorn app.main:app --port 8123`` 或 ``python -m app.main``。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.agent.checkpoint import checkpointer_manager
from app.api import ai_router, health_router
from app.config import get_settings
from app.llm import LLMNotConfiguredError
from app.logging_setup import configure_logging
from app.middleware import RequestLoggingMiddleware

logger = logging.getLogger(__name__)

DESCRIPTION = """
基于 **FastAPI + LangChain + LangGraph** 的 AI 超级智能体应用。

- **AI 运动健康助手（FitApp）**：多轮对话、RAG 知识库、工具调用、MCP
- **AI 超级智能体（TealManus）**：LangGraph StateGraph 编排的 Think–Act 自主规划智能体
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    settings = get_settings()
    if not settings.llm_configured:
        logger.warning(
            "未配置大模型凭证（DASHSCOPE_API_KEY / LLM_PROVIDER=ollama），"
            "/ai/** 接口会返回 503；其余接口与文档仍可正常访问"
        )
    await checkpointer_manager.startup()
    logger.info("%s 启动完成", settings.app_name)
    try:
        yield
    finally:
        await checkpointer_manager.shutdown()
        logger.info("%s 已停止", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    prefix = settings.api_prefix.rstrip("/")

    application = FastAPI(
        title="Teal AI Agent",
        description=DESCRIPTION,
        version=settings.app_version,
        lifespan=lifespan,
        openapi_url=f"{prefix}/v3/api-docs",
        docs_url=f"{prefix}/swagger-ui.html",
        redoc_url=None,
    )

    # 全局跨域：允许携带凭证的跨域访问
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_pattern,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(ai_router, prefix=prefix)
    application.include_router(health_router, prefix=prefix)

    @application.exception_handler(LLMNotConfiguredError)
    async def _llm_not_configured(_: Request, exc: LLMNotConfiguredError) -> JSONResponse:
        logger.error("大模型未配置：%s", exc)
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url=f"{prefix}/swagger-ui.html")

    return application


app = create_app()


def main() -> None:
    """本地调试入口：``python -m app.main``。"""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.server_port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
