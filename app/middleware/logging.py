"""调用日志中间件。

用纯 ASGI 中间件实现（而不是 BaseHTTPMiddleware），避免包装 SSE 流式响应时
产生额外的缓冲；同时记录耗时、状态码与关键入参，便于线上排障。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.access")

_PREVIEW_LIMIT = 60
_IGNORED_PATHS = ("/health", "/docs", "/openapi.json", "/swagger-ui.html")


def _preview(value: str) -> str:
    return value if len(value) <= _PREVIEW_LIMIT else f"{value[:_PREVIEW_LIMIT]}…"


class RequestLoggingMiddleware:
    """记录每一次 HTTP 调用的方法、路径、状态、耗时与会话信息。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        skip = any(path.endswith(suffix) for suffix in _IGNORED_PATHS)
        started = time.perf_counter()
        status_code: dict[str, int] = {}
        error: BaseException | None = None

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code["value"] = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except BaseException as exc:  # noqa: BLE001 - 记录后继续抛出
            error = exc
            raise
        finally:
            if not skip:
                elapsed_ms = (time.perf_counter() - started) * 1000
                query = scope.get("query_string", b"").decode("utf-8", "ignore")
                extra: dict[str, Any] = {}
                for pair in query.split("&"):
                    key, _, value = pair.partition("=")
                    if key in {"chatId", "message"} and value:
                        extra[key] = _preview(value) if key == "message" else value
                logger.info(
                    "%s %s -> %s | %.1f ms | %s",
                    scope.get("method", ""),
                    path,
                    status_code.get("value", "-"),
                    elapsed_ms,
                    extra or "-",
                )
                if error is not None:
                    logger.error("请求异常：%s %s | %s", scope.get("method", ""), path, error)
