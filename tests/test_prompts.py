"""提示词完整性测试。

重构原则：提示词与知识库文档内容不允许被改写。这里对关键文案做守护，
一旦被改动会直接失败，避免「重构」悄悄改变模型行为。
"""

from __future__ import annotations

from app import prompts


def test_fit_app_system_prompt_intact() -> None:
    text = prompts.FIT_APP_SYSTEM_PROMPT
    assert text.startswith("扮演深耕运动科学与健康管理领域的专家。")
    assert "1. 确认核心诉求（减脂/增肌/专项体能）" in text
    assert "2. 评估身体阶段（新手/进阶/康复）" in text
    assert text.endswith("以便给出兼顾安全性与有效性的专属运动与健康管理方案。")


def test_fit_app_report_prompt_appends_suffix() -> None:
    assert prompts.FIT_APP_REPORT_SYSTEM_PROMPT == (
        prompts.FIT_APP_SYSTEM_PROMPT + prompts.FIT_APP_REPORT_SYSTEM_SUFFIX
    )
    assert prompts.FIT_APP_REPORT_SYSTEM_SUFFIX == (
        "每次对话后都要生成运动健康结果，标题为{用户名}的运动健康报告，内容为建议列表"
    )


def test_teal_manus_prompts_intact() -> None:
    assert prompts.TEAL_MANUS_SYSTEM_PROMPT == (
        "You are TealManus, an all-capable AI assistant, aimed at solving any task presented by the user.\n"
        "You have various tools at your disposal that you can call upon to efficiently complete complex requests.\n"
    )
    assert prompts.TEAL_MANUS_NEXT_STEP_PROMPT == (
        "Based on user needs, proactively select the most appropriate tool or combination of tools.\n"
        "For complex tasks, you can break down the problem and use different tools step by step to solve it.\n"
        "After using each tool, clearly explain the execution results and suggest the next steps.\n"
        "If you want to stop the interaction at any point, use the `terminate` tool/function call.\n"
    )


def test_re_reading_and_terminate_prompts_intact() -> None:
    assert prompts.RE_READING_TEMPLATE == "{user_text}\nRead the question again: {user_text}\n"
    assert prompts.TERMINATE_TOOL_DESCRIPTION == (
        "Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.\n"
        '"When you have finished all the tasks, call this tool to end the work.\n'
    )
    assert prompts.TERMINATE_TOOL_NAME == "doTerminate"


def test_empty_context_prompt_intact() -> None:
    assert prompts.EMPTY_CONTEXT_PROMPT == (
        "你应该输出下面的内容：\n"
        "抱歉，我只能回答运动与健康管理相关的问题，别的没办法帮到您哦，\n"
        "有问题可以访问项目主页 https://github.com/Teal-loading/ai-agent-one\n"
    )


def test_agent_messages_intact() -> None:
    messages = prompts.AgentMessages
    assert messages.CANNOT_RUN_WITH_EMPTY_PROMPT == "Cannot run agent with empty user prompt"
    assert messages.THINK_DONE_WITHOUT_ACTION == "思考完成 - 无需行动"
    assert messages.NO_TOOL_TO_CALL == "没有工具需要调用"
    assert messages.TOOL_RESULT.format(name="x", result="y") == "工具 x 返回的结果：y"
    assert messages.MAX_STEPS_REACHED.format(max_steps=20) == "Terminated: Reached max steps (20)"
    assert messages.STREAM_MAX_STEPS_REACHED.format(max_steps=20) == "执行结束：达到最大步骤（20）"
