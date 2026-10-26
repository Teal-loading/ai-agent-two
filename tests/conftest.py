"""pytest 公共配置与夹具。"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """隔离配置与单例，保证用例之间互不影响、不触碰真实外部依赖。"""
    monkeypatch.setenv("FILE_SAVE_DIR", str(tmp_path / "tmp"))
    monkeypatch.setenv("CHAT_MEMORY_DIR", str(tmp_path / "chat-memory"))
    monkeypatch.setenv("CHAT_MEMORY", "memory")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "dashscope")
    monkeypatch.setenv("VECTOR_STORE", "memory")
    monkeypatch.setenv("MANUS_CHECKPOINTER", "memory")
    monkeypatch.setenv("MANUS_MAX_STEPS", "5")

    from app.agent import reset_teal_manus
    from app.apps import reset_fit_app
    from app.config import reset_settings_cache
    from app.llm import clear_model_cache
    from app.memory import reset_chat_memory
    from app.rag import reset_vector_store_manager

    reset_settings_cache()
    clear_model_cache()
    reset_chat_memory()
    reset_vector_store_manager()
    reset_fit_app()
    reset_teal_manus()
    yield
    reset_settings_cache()
    clear_model_cache()
    reset_chat_memory()


@pytest.fixture
def docs_dir() -> Path:
    from app.config import DOCUMENT_DIR

    return Path(DOCUMENT_DIR)
