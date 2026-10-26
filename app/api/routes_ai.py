"""AI 接口。

接口路径与参数名（``message``、``chatId``）是对前端的稳定契约，请勿改动。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.agent.teal_manus import get_teal_manus
from app.api.sse import sse_response
from app.apps.fit_app import FitReport, get_fit_app, new_chat_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def _chat_id(chat_id: str | None, prefix: str) -> str:
    return chat_id or new_chat_id(prefix)


@router.get(
    "/fit_app/chat/sync",
    summary="同步调用 AI 运动健康助手",
    response_class=PlainTextResponse,
)
async def chat_with_fit_app_sync(
    message: str = Query(..., description="用户消息"),
    chatId: str | None = Query(None, alias="chatId", description="会话 ID"),
) -> PlainTextResponse:
    fit_app = get_fit_app()
    return PlainTextResponse(await fit_app.do_chat(message, _chat_id(chatId, "fit")))


@router.get("/fit_app/chat/sse", summary="SSE 流式调用 AI 运动健康助手")
async def chat_with_fit_app_sse(
    message: str = Query(..., description="用户消息"),
    chatId: str | None = Query(None, alias="chatId", description="会话 ID"),
):
    fit_app = get_fit_app()
    return sse_response(fit_app.do_chat_stream(message, _chat_id(chatId, "fit")))


@router.get(
    "/fit_app/chat/server_sent_event",
    summary="SSE 流式调用（ServerSentEvent 语义，与 /sse 等价）",
)
async def chat_with_fit_app_server_sent_event(
    message: str = Query(..., description="用户消息"),
    chatId: str | None = Query(None, alias="chatId", description="会话 ID"),
):
    fit_app = get_fit_app()
    return sse_response(fit_app.do_chat_stream(message, _chat_id(chatId, "fit")))


@router.get(
    "/fit_app/chat/sse_emitter",
    summary="SSE 流式调用（SseEmitter 语义，与 /sse 等价）",
)
async def chat_with_fit_app_sse_emitter(
    message: str = Query(..., description="用户消息"),
    chatId: str | None = Query(None, alias="chatId", description="会话 ID"),
):
    fit_app = get_fit_app()
    return sse_response(fit_app.do_chat_stream(message, _chat_id(chatId, "fit")))


@router.post("/fit_app/chat/report", summary="结构化输出：运动健康报告")
async def chat_with_fit_app_report(
    message: str = Query(..., description="用户消息"),
    chatId: str | None = Query(None, alias="chatId", description="会话 ID"),
) -> FitReport:
    fit_app = get_fit_app()
    return await fit_app.do_chat_with_report(message, _chat_id(chatId, "fit"))


@router.get("/manus/chat", summary="SSE 流式调用 Manus 超级智能体")
async def chat_with_manus(
    message: str = Query(..., description="用户任务描述"),
    chatId: str | None = Query(None, alias="chatId", description="会话/线程 ID，用于状态恢复"),
):
    manus = get_teal_manus()
    return sse_response(manus.run_stream(message, thread_id=chatId))
