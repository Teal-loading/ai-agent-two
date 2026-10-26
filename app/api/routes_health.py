"""健康检查接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.apps.fit_app import settings_summary

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="健康检查", response_class=PlainTextResponse)
async def health_check() -> PlainTextResponse:
    return PlainTextResponse("ok")


@router.get("/details", summary="运行配置摘要（排障用，不含密钥）")
async def health_details() -> dict[str, Any]:
    return settings_summary()
