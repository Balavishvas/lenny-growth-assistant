"""Tests for RAG chat routing and persistence without a live Ollama server."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import main  # noqa: E402
from app.database import Base, engine  # noqa: E402

client = TestClient(main.app)

FAKE_SOURCE = {
    "chunk_id": "chunk-1",
    "source_id": "episode-1",
    "source_type": "podcast",
    "title": "Building Great Products",
    "guest": "Jane Doe",
    "url": "https://example.com/episode",
    "publish_date": "2025-01-02",
    "chunk_index": 0,
    "content": "Strong products solve a frequent and important user problem.",
    "distance": 0.12,
}


def _new_session() -> str:
    Base.metadata.create_all(bind=engine)
    response = client.post("/api/v1/sessions", json={"title": "Chat test", "metadata": {}})
    assert response.status_code == 201
    return response.json()["id"]


def test_chat_endpoint_uses_retrieved_evidence_and_returns_sources(monkeypatch):
    session_id = _new_session()
    captured = {}

    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    def fake_generate(messages):
        captured["messages"] = messages
        return "A strong product solves an important user problem [1]."

    monkeypatch.setattr(main, "generate_reply", fake_generate)

    response = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "message": "What makes a strong product?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].endswith("[1].")
    assert payload["grounded"] is True
    assert payload["sources"][0]["title"] == "Building Great Products"
    assert "Retrieved evidence:" in captured["messages"][0]["content"]
    assert "Strong products solve a frequent and important user problem." in captured["messages"][0]["content"]

    history = client.get(f"/api/v1/sessions/{session_id}").json()
    assert [item["role"] for item in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["message_metadata"]["sources"][0]["chunk_id"] == "chunk-1"


def test_chat_returns_honest_fallback_when_no_evidence(monkeypatch):
    session_id = _new_session()
    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [])

    def fail_if_called(messages):
        raise AssertionError("LLM should not be called when retrieval returns no evidence")

    monkeypatch.setattr(main, "generate_reply", fail_if_called)

    response = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "message": "Tell me a specific fact not in the corpus"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["grounded"] is False
    assert payload["sources"] == []
    assert "couldn't find enough relevant evidence" in payload["answer"]


def test_chat_endpoint_returns_404_for_unknown_session():
    response = client.post(
        "/api/v1/chat",
        json={"session_id": "missing-session", "message": "Hello"},
    )
    assert response.status_code == 404


def test_list_sessions_returns_recent_conversations():
    session_id = _new_session()

    response = client.get("/api/v1/sessions")

    assert response.status_code == 200
    assert any(item["id"] == session_id for item in response.json())


def test_stream_chat_returns_tokens_and_latency_metadata(monkeypatch):
    session_id = _new_session()
    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])
    monkeypatch.setattr(main, "stream_reply", lambda messages: iter(["A grounded ", "answer [1]."]))

    response = client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "message": "What makes a strong product?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "token"' in response.text
    assert "A grounded " in response.text
    assert '"type": "done"' in response.text
    assert '"retrieval_ms"' in response.text
    history = client.get(f"/api/v1/sessions/{session_id}").json()
    assert history["messages"][-1]["content"] == "A grounded answer [1]."
