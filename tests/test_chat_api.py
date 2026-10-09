"""Tests for chat API routing and persistence without a live Ollama server."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import main  # noqa: E402
from app.models import ChatMessage, ChatSession  # noqa: E402
from app.database import Base, engine  # noqa: E402

client = TestClient(main.app)


def test_chat_endpoint_returns_and_persists_assistant_reply(monkeypatch):
    Base.metadata.create_all(bind=engine)
    created = client.post("/api/v1/sessions", json={"title": "Chat test", "metadata": {}})
    assert created.status_code == 201
    session_id = created.json()["id"]

    monkeypatch.setattr(main, "generate_reply", lambda messages: "Measure activation and retention.")

    response = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "message": "What should a startup measure?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Measure activation and retention."
    assert payload["session_id"] == session_id
    history = client.get(f"/api/v1/sessions/{session_id}").json()
    assert [item["role"] for item in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["content"] == "Measure activation and retention."


def test_chat_endpoint_returns_404_for_unknown_session():
    response = client.post(
        "/api/v1/chat",
        json={"session_id": "missing-session", "message": "Hello"},
    )
    assert response.status_code == 404
