"""SSE 工具。

输出格式为 ``data:<chunk>\\n\\n``，与前端 ``EventSource`` 的约定保持一致；
结束时额外推送 ``[DONE]``，让前端可以立即收尾。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

SSE_DONE = "[DONE]"
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    # 关闭 Nginx 等反向代理的缓冲，保证增量推送
    "X-Accel-Buffering": "no",
}


def format_sse(data: str) -> str:
    """把一段文本编码为 SSE 事件（多行内容拆成多条 data 行，客户端会自动拼回）。"""
    lines = data.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


def sse_response(source: AsyncIterator[str]) -> StreamingResponse:
    """把异步文本流包装为 ``text/event-stream`` 响应。"""

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in source:
                if not chunk:
                    continue
                yield format_sse(chunk)
        except asyncio.CancelledError:  # 客户端断开
            raise
        except Exception as exc:  # noqa: BLE001 - 流式响应已开始，只能以文本告知错误
            logger.exception("SSE 流式输出异常")
            yield format_sse(f"执行错误：{exc}")
        yield format_sse(SSE_DONE)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
