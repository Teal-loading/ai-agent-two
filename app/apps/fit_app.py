"""AI 运动健康助手。

能力矩阵：

===================  =========================================
接口方法             说明
===================  =========================================
do_chat              基础多轮对话（带窗口记忆）
do_chat_stream       流式对话（SSE）
do_chat_with_report  结构化输出（运动健康报告）
do_chat_with_rag     RAG 知识库问答（查询重写 + 向量检索）
do_chat_with_tools   本地工具调用
do_chat_with_mcp     MCP 服务调用
===================  =========================================
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.advisor import logger_callbacks
from app.agent.nodes import extract_text
from app.config import get_settings
from app.llm import get_chat_model
from app.mcp import get_mcp_tool_provider
from app.memory import WindowChatMemory, get_chat_memory
from app.prompts import (
    EMPTY_CONTEXT_PROMPT,
    FIT_APP_REPORT_SYSTEM_PROMPT,
    FIT_APP_SYSTEM_PROMPT,
)
from app.rag import FitAppRagCustomAdvisor, RagService
from app.tools.registry import get_tools

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


class FitReport(BaseModel):
    """运动健康报告（结构化输出）。"""

    title: str = Field(default="", description="运动健康报告标题")
    suggestions: list[str] = Field(default_factory=list, description="运动健康建议列表")


class FitApp:
    """AI 运动健康助手。"""

    name = "fitApp"

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        stream_llm: BaseChatModel | None = None,
        memory: WindowChatMemory | None = None,
        rag: RagService | None = None,
        tools: list[BaseTool] | None = None,
    ) -> None:
        self._llm = llm if llm is not None else get_chat_model()
        if stream_llm is not None:
            self._stream_llm = stream_llm
        elif llm is not None:
            self._stream_llm = llm
        else:
            self._stream_llm = get_chat_model(streaming=True)
        self._memory = memory or get_chat_memory()
        self._rag = rag or RagService()
        self._tools = tools if tools is not None else list(get_tools())
        self._mcp = get_mcp_tool_provider()

    # ------------------------------------------------------------------
    # 通用工具方法
    # ------------------------------------------------------------------
    def _messages(
        self,
        chat_id: str,
        user_content: str,
        system_prompt: str = FIT_APP_SYSTEM_PROMPT,
        with_history: bool = True,
    ) -> list[BaseMessage]:
        history = self._memory.get(chat_id) if with_history else []
        return [SystemMessage(content=system_prompt), *history, HumanMessage(content=user_content)]

    def _remember(self, chat_id: str, user_text: str, assistant_text: str) -> None:
        self._memory.add(
            chat_id,
            [HumanMessage(content=user_text), AIMessage(content=assistant_text)],
        )

    async def _invoke_with_tools(
        self,
        messages: list[BaseMessage],
        tools: list[BaseTool],
        max_rounds: int = MAX_TOOL_ROUNDS,
    ) -> str:
        """工具调用循环：调用模型 → 执行工具 → 回填结果 → 再调用模型。"""
        tool_map = {tool.name: tool for tool in tools}
        llm = self._llm.bind_tools(tools) if tools else self._llm
        conversation = list(messages)
        text = ""

        for _ in range(max_rounds):
            response = await llm.ainvoke(conversation, config={"callbacks": logger_callbacks()})
            conversation.append(response)
            text = extract_text(response.content)
            tool_calls = list(getattr(response, "tool_calls", None) or [])
            if not tool_calls:
                return text

            for call in tool_calls:
                name = str(call.get("name"))
                tool = tool_map.get(name)
                if tool is None:
                    output = f"Error: tool {name} not found"
                else:
                    try:
                        output = await tool.ainvoke(call.get("args") or {})
                    except Exception as exc:  # noqa: BLE001 - 工具异常回传给模型
                        logger.exception("工具 %s 执行失败", name)
                        output = f"Error executing tool {name}: {exc}"
                if not isinstance(output, str):
                    output = json.dumps(output, ensure_ascii=False, default=str)
                conversation.append(ToolMessage(content=output, tool_call_id=str(call.get("id")), name=name))
        return text

    # ------------------------------------------------------------------
    # 1. 基础对话
    # ------------------------------------------------------------------
    async def do_chat(self, message: str, chat_id: str) -> str:
        """AI 基础对话（支持多轮对话记忆）。"""
        messages = self._messages(chat_id, message)
        response = await self._llm.ainvoke(messages, config={"callbacks": logger_callbacks()})
        content = extract_text(response.content)
        logger.info("content: %s", content)
        self._remember(chat_id, message, content)
        return content

    async def do_chat_stream(self, message: str, chat_id: str) -> AsyncIterator[str]:
        """AI 基础对话（支持多轮对话记忆，SSE 流式传输）。"""
        messages = self._messages(chat_id, message)
        chunks: list[str] = []
        try:
            async for chunk in self._stream_llm.astream(messages, config={"callbacks": logger_callbacks()}):
                piece = extract_text(chunk.content)
                if piece:
                    chunks.append(piece)
                    yield piece
        finally:
            if chunks:
                self._remember(chat_id, message, "".join(chunks))

    # ------------------------------------------------------------------
    # 2. 结构化输出
    # ------------------------------------------------------------------
    async def do_chat_with_report(self, message: str, chat_id: str) -> FitReport:
        """AI 运动健康报告功能（实战结构化输出）。"""
        structured = self._llm.with_structured_output(FitReport)
        messages = self._messages(chat_id, message, system_prompt=FIT_APP_REPORT_SYSTEM_PROMPT)
        result = await structured.ainvoke(messages, config={"callbacks": logger_callbacks()})
        report = result if isinstance(result, FitReport) else FitReport(**dict(result))
        logger.info("fitReport: %s", report)
        self._remember(
            chat_id,
            message,
            json.dumps(report.model_dump(), ensure_ascii=False),
        )
        return report

    # ------------------------------------------------------------------
    # 3. RAG 知识库问答
    # ------------------------------------------------------------------
    async def do_chat_with_rag(self, message: str, chat_id: str) -> str:
        """和 RAG 知识库进行对话（查询重写 + 向量检索 + 上下文注入）。"""
        context = await self._rag.build(message)
        if not context.hit:
            logger.warning("知识库未召回相关内容：%s", context.query)
        messages = self._messages(chat_id, context.to_prompt())
        response = await self._llm.ainvoke(messages, config={"callbacks": logger_callbacks()})
        content = extract_text(response.content)
        logger.info("content: %s", content)
        self._remember(chat_id, message, content)
        return content

    async def do_chat_with_custom_rag(self, message: str, chat_id: str, status: str = "起步") -> str:
        """按身体阶段过滤的自定义 RAG 顾问（空上下文直接兜底，不消耗模型调用）。"""
        advisor = FitAppRagCustomAdvisor(self._rag, status=status)
        context = await advisor.build(message)
        if context is None:
            logger.info("未命中「%s」阶段的知识库内容，返回兜底文案", status)
            self._remember(chat_id, message, EMPTY_CONTEXT_PROMPT)
            return EMPTY_CONTEXT_PROMPT

        messages = self._messages(chat_id, context.to_prompt())
        response = await self._llm.ainvoke(messages, config={"callbacks": logger_callbacks()})
        content = extract_text(response.content)
        self._remember(chat_id, message, content)
        return content

    # ------------------------------------------------------------------
    # 4. 工具 / MCP 调用
    # ------------------------------------------------------------------
    async def do_chat_with_tools(self, message: str, chat_id: str) -> str:
        """AI 运动健康报告功能（支持调用本地工具）。"""
        messages = self._messages(chat_id, message)
        content = await self._invoke_with_tools(messages, self._tools)
        logger.info("content: %s", content)
        self._remember(chat_id, message, content)
        return content

    async def do_chat_with_mcp(self, message: str, chat_id: str) -> str:
        """AI 运动健康报告功能（调用 MCP 服务）。"""
        tools = await self._mcp.get_tools()
        if not tools:
            raise RuntimeError(self._mcp.error or "MCP 工具不可用，请检查 mcp-servers.json 与 MCP 服务状态")
        messages = self._messages(chat_id, message)
        content = await self._invoke_with_tools(messages, tools)
        logger.info("content: %s", content)
        self._remember(chat_id, message, content)
        return content


_fit_app: FitApp | None = None


def get_fit_app() -> FitApp:
    """返回 FitApp 单例。"""
    global _fit_app
    if _fit_app is None:
        _fit_app = FitApp()
    return _fit_app


def reset_fit_app() -> None:
    global _fit_app
    _fit_app = None


def new_chat_id(prefix: str = "fit") -> str:
    """生成会话 ID（前端未传 chatId 时使用）。"""
    return f"{prefix}_{uuid4().hex[:8]}"


def settings_summary() -> dict[str, Any]:
    """返回关键配置摘要，便于健康检查/排障。"""
    settings = get_settings()
    return {
        "llm_provider": settings.llm_provider,
        "chat_model": settings.chat_model,
        "vector_store": settings.vector_store,
        "chat_memory": settings.chat_memory,
        "manus_checkpointer": settings.manus_checkpointer,
        "llm_configured": settings.llm_configured,
    }
