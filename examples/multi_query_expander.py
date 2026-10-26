"""示例：多查询扩展（Multi-Query Expander）。

把一个用户问题扩展成多个检索视角，再分别做向量检索，可以显著提升召回率。

运行：
    python examples/multi_query_expander.py
"""

from __future__ import annotations

import asyncio

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.llm import get_chat_model
from app.prompts import MULTI_QUERY_EXPAND_PROMPT

QUESTION = "谁是程序猿Teal啊？"


async def expand(query: str, count: int = 3) -> list[str]:
    chain = ChatPromptTemplate.from_template(MULTI_QUERY_EXPAND_PROMPT) | get_chat_model() | StrOutputParser()
    text = await chain.ainvoke({"count": count, "query": query})
    variants = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    return variants[:count]


async def main() -> None:
    for index, variant in enumerate(await expand(QUESTION), start=1):
        print(f"{index}. {variant}")


if __name__ == "__main__":
    asyncio.run(main())
