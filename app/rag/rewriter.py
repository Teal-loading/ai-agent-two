"""查询重写器。

把用户口语化的问题改写为更适合向量检索的查询，
模型不可用或调用失败时自动退化为原查询，保证检索链路可用。
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.llm import get_chat_model
from app.prompts import QUERY_REWRITE_PROMPT

logger = logging.getLogger(__name__)


class QueryRewriter:
    """面向向量检索的查询改写。"""

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self._llm = llm
        self._chain = None

    def _get_chain(self):
        if self._chain is None:
            llm = self._llm or get_chat_model()
            self._chain = ChatPromptTemplate.from_template(QUERY_REWRITE_PROMPT) | llm | StrOutputParser()
        return self._chain

    async def rewrite(self, prompt: str) -> str:
        """执行查询重写；失败返回原查询。"""
        if not prompt or not prompt.strip():
            return prompt
        try:
            rewritten = await self._get_chain().ainvoke({"query": prompt})
        except Exception as exc:  # noqa: BLE001 - 检索增强降级
            logger.warning("查询重写失败，使用原始查询：%s", exc)
            return prompt
        rewritten = (rewritten or "").strip()
        logger.debug("查询重写：%s -> %s", prompt, rewritten)
        return rewritten or prompt
