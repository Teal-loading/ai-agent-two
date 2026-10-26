"""``app.middleware`` —— ASGI 中间件。"""

from app.middleware.logging import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware"]
