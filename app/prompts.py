"""集中管理的提示词与模型可见文案。

.. important::

   本文件中的提示词属于对外契约内容，不允许随意改写。``tests/test_prompts.py``
   会对关键文案做守护，改动会直接导致测试失败。
"""

from __future__ import annotations

# ======================================================================
# AI 运动健康助手（FitApp）
# ======================================================================
FIT_APP_SYSTEM_PROMPT = (
    "扮演深耕运动科学与健康管理领域的专家。开场向用户表明身份，告知用户可咨询运动规划与健康难题。"
    "围绕用户的核心诉求与身体阶段两个维度进行交叉提问："
    "1. 确认核心诉求（减脂/增肌/专项体能）：询问减脂期的热量与饥饿感控制、增肌期的力量突破与肌肉感受度，或专项运动（如游泳、篮球、羽毛球）的体能与耐力痛点。"
    "2. 评估身体阶段（新手/进阶/康复）：询问新手在基础动作发力与习惯培养上的困扰、进阶者在训练容量与动作周期上的瓶颈，以及康复人群的关节受限、陈旧伤病或体态代偿问题。"
    "引导用户明确自身的“诉求+阶段”，并详述身体数据（身高/体重/体脂）、日常训练与饮食明细及既往伤病史，以便给出兼顾安全性与有效性的专属运动与健康管理方案。"
)

# 结构化输出（运动健康报告）时追加在系统提示词后的内容
FIT_APP_REPORT_SYSTEM_SUFFIX = "每次对话后都要生成运动健康结果，标题为{用户名}的运动健康报告，内容为建议列表"

FIT_APP_REPORT_SYSTEM_PROMPT = FIT_APP_SYSTEM_PROMPT + FIT_APP_REPORT_SYSTEM_SUFFIX

# ======================================================================
# AI 超级智能体（TealManus）
# ======================================================================
TEAL_MANUS_SYSTEM_PROMPT = (
    "You are TealManus, an all-capable AI assistant, aimed at solving any task presented by the user.\n"
    "You have various tools at your disposal that you can call upon to efficiently complete complex requests.\n"
)

TEAL_MANUS_NEXT_STEP_PROMPT = (
    "Based on user needs, proactively select the most appropriate tool or combination of tools.\n"
    "For complex tasks, you can break down the problem and use different tools step by step to solve it.\n"
    "After using each tool, clearly explain the execution results and suggest the next steps.\n"
    "If you want to stop the interaction at any point, use the `terminate` tool/function call.\n"
)

# ======================================================================
# Advisor：日志与推理增强
# ======================================================================
RE_READING_TEMPLATE = "{user_text}\nRead the question again: {user_text}\n"

# ======================================================================
# RAG
# ======================================================================
# 检索为空时的兜底回答
EMPTY_CONTEXT_PROMPT = (
    "你应该输出下面的内容：\n"
    "抱歉，我只能回答运动与健康管理相关的问题，别的没办法帮到您哦，\n"
    "有问题可以访问项目主页 https://github.com/Teal-loading/ai-agent-one\n"
)

# RAG 问答模板
QA_PROMPT_TEMPLATE = (
    "{query}\n\n"
    "Context information is below, surrounded by ---------------------\n"
    "---------------------\n"
    "{question_answer_context}\n"
    "---------------------\n"
    "Given the context and provided history information and not prior knowledge,\n"
    "reply to the user comment. If the answer is not in the context, inform\n"
    "the user that you can't answer the question.\n"
)

# 查询改写（RewriteQueryTransformer 的等价实现）
QUERY_REWRITE_PROMPT = (
    "Given a user query, rewrite it to provide better results when querying a vector store.\n"
    "Ensure the rewritten query preserves the original intent but is optimized for semantic search.\n"
    "Do not answer the query, only rewrite it.\n\n"
    "User query: {query}\n"
)

# 关键词元信息增强（KeywordMetadataEnricher 的等价实现）
KEYWORD_ENRICH_PROMPT = (
    "Extract {count} keywords from the following text.\n"
    "Return them as a comma-separated list without any explanations.\n\n"
    "Text:\n{text}\n"
)

# 多查询扩展 Demo（examples/multi_query_expander.py）使用
MULTI_QUERY_EXPAND_PROMPT = (
    "Generate {count} different versions of the given user question to retrieve relevant documents "
    "from a vector database.\n"
    "By generating multiple perspectives on the user question, your goal is to help the user "
    "overcome some of the limitations of distance based similarity search.\n"
    "Provide these alternative questions separated by newlines.\n"
    "Original question: {query}\n"
)

# ======================================================================
# 工具描述（模型可见 schema）
# ======================================================================
TERMINATE_TOOL_NAME = "doTerminate"

TERMINATE_TOOL_DESCRIPTION = (
    "Terminate the interaction when the request is met OR if the assistant cannot proceed further with the task.\n"
    '"When you have finished all the tasks, call this tool to end the work.\n'
)

TERMINATE_TOOL_RESULT = "任务结束"

# ======================================================================
# 智能体运行期文案
# ======================================================================
class AgentMessages:
    """智能体执行过程中的固定文案。"""

    CANNOT_RUN_FROM_STATE = "Cannot run agent from state: "
    CANNOT_RUN_WITH_EMPTY_PROMPT = "Cannot run agent with empty user prompt"
    STREAM_CANNOT_RUN_FROM_STATE = "错误：无法从状态运行代理："
    STREAM_CANNOT_RUN_WITH_EMPTY_PROMPT = "错误：不能使用空提示词运行代理"
    EXECUTION_ERROR = "执行错误"
    STREAM_EXECUTION_ERROR = "执行错误："
    THINK_DONE_WITHOUT_ACTION = "思考完成 - 无需行动"
    STEP_FAILED = "步骤执行失败："
    NO_TOOL_TO_CALL = "没有工具需要调用"
    TOOL_RESULT = "工具 {name} 返回的结果：{result}"
    MAX_STEPS_REACHED = "Terminated: Reached max steps ({max_steps})"
    STREAM_MAX_STEPS_REACHED = "执行结束：达到最大步骤（{max_steps}）"
    THINK_ERROR = "处理时遇到了错误："
