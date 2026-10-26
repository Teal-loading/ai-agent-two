"""LangGraph Think–Act 循环测试（使用脚本化模型，无需真实 API Key）。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agent.teal_manus import AgentRunError, TealManus
from app.tools import get_tools
from tests.fakes import ScriptedChatModel, tool_call_message


def build_manus(responses: list[AIMessage], max_steps: int = 5) -> tuple[TealManus, ScriptedChatModel]:
    model = ScriptedChatModel(responses=responses)
    manus = TealManus(llm=model, tools=list(get_tools()), max_steps=max_steps)
    return manus, model


async def test_think_act_loop() -> None:
    manus, model = build_manus(
        [
            tool_call_message("generatePDF", {"fileName": "plan.pdf", "content": "四周计划"}),
            AIMessage(content="已为你生成训练计划 PDF"),
        ]
    )

    result = await manus.run("帮我生成一份四周训练计划 PDF")

    assert "Step 1: 工具 generatePDF 返回的结果：" in result
    assert "PDF generated successfully" in result
    assert "Step 2: 已为你生成训练计划 PDF" in result
    assert model.calls == 2


async def test_terminate_stops_loop() -> None:
    manus, model = build_manus(
        [
            tool_call_message("doTerminate", {}),
            AIMessage(content="这段内容不应该被调用"),
        ]
    )

    result = await manus.run("任务完成了")

    assert "任务结束" in result
    assert model.calls == 1
    assert "这段内容不应该被调用" not in result


async def test_max_steps_terminates() -> None:
    manus, model = build_manus(
        [tool_call_message("readFile", {"fileName": "a.txt"}, call_id=f"c{i}") for i in range(5)]
        + [AIMessage(content="结束")],
        max_steps=2,
    )

    result = await manus.run("一直读文件")

    assert "Terminated: Reached max steps (2)" in result
    assert model.calls == 2


async def test_stream_emits_steps() -> None:
    manus, _ = build_manus(
        [
            tool_call_message("doTerminate", {}),
        ]
    )

    chunks = [chunk async for chunk in manus.run_stream("收尾")]

    assert chunks
    assert chunks[0].startswith("Step 1: 工具 doTerminate")
    assert chunks[-1].endswith("任务结束")


async def test_empty_prompt_rejected() -> None:
    manus, _ = build_manus([AIMessage(content="不会被调用")])
    try:
        await manus.run("   ")
    except AgentRunError as exc:
        assert str(exc) == "Cannot run agent with empty user prompt"
    else:  # pragma: no cover - 断言分支
        raise AssertionError("空提示词应当被拒绝")


async def test_stream_empty_prompt_returns_message() -> None:
    manus, _ = build_manus([AIMessage(content="不会被调用")])
    chunks = [chunk async for chunk in manus.run_stream("")]
    assert chunks == ["错误：不能使用空提示词运行代理"]


async def test_think_error_is_reported() -> None:
    class BrokenModel(ScriptedChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise RuntimeError("模型服务不可用")

    manus = TealManus(llm=BrokenModel(responses=[]), tools=list(get_tools()), max_steps=3)
    result = await manus.run("你好")

    assert "处理时遇到了错误：模型服务不可用" in result
