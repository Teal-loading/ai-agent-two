"""会话记忆测试：窗口裁剪 + 文件持久化。"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from app.memory.chat_memory import FileMessageStore, WindowChatMemory


def test_window_trimming() -> None:
    memory = WindowChatMemory(max_messages=4)
    for index in range(3):
        memory.add("chat-1", [HumanMessage(content=f"q{index}"), AIMessage(content=f"a{index}")])

    history = memory.get("chat-1")
    assert len(history) == 4
    assert history[-1].content == "a2"
    assert history[0].content == "q1"


def test_clear() -> None:
    memory = WindowChatMemory(max_messages=10)
    memory.add("chat-1", [HumanMessage(content="hello")])
    memory.clear("chat-1")
    assert memory.get("chat-1") == []


def test_file_store_roundtrip(tmp_path: Path) -> None:
    store = FileMessageStore(tmp_path / "memory")
    memory = WindowChatMemory(store=store, max_messages=10)
    memory.add("fit_abc", [HumanMessage(content="我想减脂"), AIMessage(content="先控制热量缺口")])

    # 新实例（模拟进程重启）仍能读回上下文
    reopened = WindowChatMemory(store=FileMessageStore(tmp_path / "memory"), max_messages=10)
    history = reopened.get("fit_abc")
    assert [message.content for message in history] == ["我想减脂", "先控制热量缺口"]

    files = list((tmp_path / "memory").glob("*.json"))
    assert len(files) == 1


def test_file_store_sanitizes_conversation_id(tmp_path: Path) -> None:
    store = FileMessageStore(tmp_path / "memory")
    store.save("../evil", [HumanMessage(content="x")])
    saved = list((tmp_path / "memory").glob("*.json"))
    assert len(saved) == 1
    assert saved[0].parent == tmp_path / "memory"
