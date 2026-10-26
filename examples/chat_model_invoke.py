"""示例：通过统一的大模型工厂调用（LangChain ChatModel）。

运行：
    python examples/chat_model_invoke.py
"""

from __future__ import annotations

import asyncio

from app.llm import get_chat_model


async def main() -> None:
    llm = get_chat_model()
    answer = await llm.ainvoke("你好，我是Teal")
    print(answer.content)


if __name__ == "__main__":
    asyncio.run(main())
