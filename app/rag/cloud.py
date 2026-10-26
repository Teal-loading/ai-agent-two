"""基于阿里云百炼「应用」的云端知识库增强。

云端知识库是可选项，默认走本地向量库。启用方式：

1. 在百炼控制台创建「应用」，上传知识库并发布
2. 配置 ``DASHSCOPE_APP_ID``（可选 ``DASHSCOPE_KNOWLEDGE_INDEX`` 仅作说明用途）

未配置 ``DASHSCOPE_APP_ID`` 时 :meth:`available` 返回 False，链路自动走本地向量库。
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

APP_COMPLETION_URL = "https://dashscope.aliyuncs.com/api/v1/apps/{app_id}/completion"


class DashScopeKnowledgeAdvisor:
    """调用百炼应用完成「检索 + 生成」。"""

    def __init__(self, api_key: str | None = None, app_id: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.dashscope_api_key
        self.app_id = app_id if app_id is not None else settings.dashscope_app_id
        self.index_name = settings.dashscope_knowledge_index

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.app_id)

    async def answer(self, query: str, timeout_seconds: float = 60.0) -> str:
        """返回应用回答文本；未配置时抛出可读异常。"""
        if not self.available:
            raise RuntimeError("云端知识库未启用：请配置 DASHSCOPE_APP_ID 后重试（默认走本地 pgvector / 内存向量库）")
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                APP_COMPLETION_URL.format(app_id=self.app_id),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": {"prompt": query}, "parameters": {}},
            )
            response.raise_for_status()
            payload = response.json()
        return str((payload.get("output") or {}).get("text", ""))
