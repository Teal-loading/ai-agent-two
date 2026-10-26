"""FitApp 应用层测试：多轮记忆、流式输出、工具调用循环。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.apps.fit_app import FitApp
from app.memory.chat_memory import WindowChatMemory
from app.tools import get_tools
from tests.fakes import ScriptedChatModel, tool_call_message


def build_app(responses: list[AIMessage], max_memory: int = 10) -> tuple[FitApp, ScriptedChatModel]:
    model = ScriptedChatModel(responses=responses)
    fit_app = FitApp(
        llm=model,
        stream_llm=model,
        memory=WindowChatMemory(max_messages=max_memory),
        tools=list(get_tools()),
    )
    return fit_app, model


async def test_do_chat_keeps_history() -> None:
    fit_app, model = build_app([AIMessage(content="先控制热量缺口"), AIMessage(content="你刚才说要减脂")])

    await fit_app.do_chat("我想科学减脂", "fit_1")
    answer = await fit_app.do_chat("我的诉求是什么？", "fit_1")

    assert answer == "你刚才说要减脂"
    second_call_messages = model.seen[1]
    system_prompt = second_call_messages[0]
    assert system_prompt.type == "system"
    assert "扮演深耕运动科学与健康管理领域的专家。" in str(system_prompt.content)
    # 第二轮应带上第一轮的用户消息与回答
    assert [m.type for m in second_call_messages] == ["system", "human", "ai", "human"]
    assert second_call_messages[1].content == "我想科学减脂"
    assert second_call_messages[2].content == "先控制热量缺口"


async def test_do_chat_stream_saves_memory(tmp_path) -> None:
    from app.memory.chat_memory import FileMessageStore

    model = ScriptedChatModel(responses=[AIMessage(content="流式回答")])
    fit_app = FitApp(
        llm=model,
        stream_llm=model,
        memory=WindowChatMemory(store=FileMessageStore(tmp_path / "mem"), max_messages=10),
        tools=[],
    )

    chunks = [chunk async for chunk in fit_app.do_chat_stream("你好", "fit_stream")]

    assert "".join(chunks) == "流式回答"
    history = fit_app._memory.get("fit_stream")
    assert [message.content for message in history] == ["你好", "流式回答"]


async def test_do_chat_with_tools_executes_tool_calls() -> None:
    fit_app, model = build_app(
        [
            tool_call_message("writeFile", {"fileName": "档案.txt", "content": "身高 180 / 体重 75kg"}),
            AIMessage(content="已保存你的运动健康档案"),
        ]
    )

    answer = await fit_app.do_chat_with_tools("保存我的运动健康档案", "fit_tool")

    assert answer == "已保存你的运动健康档案"
    assert model.calls == 2
    tool_messages = [m for m in model.seen[1] if m.type == "tool"]
    assert tool_messages and "File written successfully" in str(tool_messages[0].content)


async def test_do_chat_with_rag_without_embeddings_degrades() -> None:
    """未配置 API Key 时向量库不可用，RAG 应降级为普通问答而不是抛异常。"""
    fit_app, model = build_app([AIMessage(content="请先补充身体数据")])

    answer = await fit_app.do_chat_with_rag("我是新手，怎么练力量？", "fit_rag")

    assert answer == "请先补充身体数据"
    user_message = model.seen[0][-1]
    # 上下文为空时仍按 QuestionAnswerAdvisor 模板拼装
    assert "Context information is below" in str(user_message.content)


async def test_custom_rag_returns_fallback_when_no_hit() -> None:
    fit_app, _ = build_app([AIMessage(content="不应被调用")])

    answer = await fit_app.do_chat_with_custom_rag("怎么康复？", "fit_custom", status="康复")

    assert answer.startswith("你应该输出下面的内容：")


def test_new_chat_id_prefix() -> None:
    from app.apps.fit_app import new_chat_id

    chat_id = new_chat_id("fit")
    assert chat_id.startswith("fit_")
    assert len(chat_id) > 6
