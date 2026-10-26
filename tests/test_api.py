"""HTTP 接口测试：路径、参数名、SSE 报文格式与错误处理。"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

import app.api.routes_ai as routes
from app.main import create_app


class FakeFitApp:
    async def do_chat(self, message: str, chat_id: str) -> str:
        return f"echo:{message}:{chat_id}"

    async def do_chat_stream(self, message: str, chat_id: str) -> AsyncIterator[str]:
        for chunk in ("你", "好"):
            yield chunk


class FakeManus:
    async def run_stream(self, user_prompt: str, thread_id: str | None = None) -> AsyncIterator[str]:
        yield f"Step 1: {user_prompt} | thread={thread_id}"


@pytest.fixture
def client() -> AsyncIterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.text == "ok"


def test_health_details(client: TestClient) -> None:
    payload = client.get("/api/health/details").json()
    assert payload["llm_configured"] is False
    assert payload["vector_store"] == "memory"


def test_openapi_available(client: TestClient) -> None:
    response = client.get("/api/v3/api-docs")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/ai/fit_app/chat/sse" in paths
    assert "/api/ai/manus/chat" in paths


def test_sync_chat_without_api_key_returns_503(client: TestClient) -> None:
    response = client.get("/api/ai/fit_app/chat/sync", params={"message": "你好", "chatId": "c1"})
    assert response.status_code == 503
    assert "DASHSCOPE_API_KEY" in response.json()["detail"]


def test_sync_chat(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "get_fit_app", lambda: FakeFitApp())
    response = client.get("/api/ai/fit_app/chat/sync", params={"message": "你好", "chatId": "fit_1"})
    assert response.status_code == 200
    assert response.text == "echo:你好:fit_1"


def test_sse_chat(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "get_fit_app", lambda: FakeFitApp())
    response = client.get("/api/ai/fit_app/chat/sse", params={"message": "你好", "chatId": "fit_1"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == "data: 你\n\ndata: 好\n\ndata: [DONE]\n\n"


def test_sse_aliases(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "get_fit_app", lambda: FakeFitApp())
    for path in ("/api/ai/fit_app/chat/server_sent_event", "/api/ai/fit_app/chat/sse_emitter"):
        response = client.get(path, params={"message": "你好", "chatId": "fit_1"})
        assert response.status_code == 200
        assert "[DONE]" in response.text


def test_manus_chat(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes, "get_teal_manus", lambda: FakeManus())
    response = client.get("/api/ai/manus/chat", params={"message": "制定约会计划", "chatId": "t-1"})
    assert response.status_code == 200
    assert "Step 1: 制定约会计划 | thread=t-1" in response.text
    assert "[DONE]" in response.text


def test_missing_query_param(client: TestClient) -> None:
    response = client.get("/api/ai/fit_app/chat/sync")
    assert response.status_code == 422
