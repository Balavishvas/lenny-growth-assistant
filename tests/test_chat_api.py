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

    def fake_generate(messages, on_tool_call=None):
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

    def fail_if_called(messages, on_tool_call=None):
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
    monkeypatch.setattr(main, "stream_reply", lambda messages, on_tool_call=None: iter(["A grounded ", "answer [1]."]))

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


def test_stream_chat_collects_custom_tool_sources(monkeypatch):
    session_id = _new_session()
    tool_source = {
        "chunk_id": "chunk-tool-2",
        "source_id": "episode-tool",
        "source_type": "podcast",
        "title": "Scaling Beyond PMF",
        "guest": "Alex Smith",
        "url": "https://example.com/tool-episode",
        "publish_date": "2025-02-15",
        "chunk_index": 1,
        "content": "Activation is secondary until product market fit is locked in.",
        "distance": 0.08,
    }

    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    def fake_stream(messages, on_tool_call=None):
        if on_tool_call:
            on_tool_call("search_lenny_transcripts", {"query": "scaling"}, [tool_source])
        yield "Tool-grounded answer [2]."

    monkeypatch.setattr(main, "stream_reply", fake_stream)

    response = client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "message": "Search transcripts for scaling beyond PMF"},
    )

    assert response.status_code == 200
    assert '"type": "done"' in response.text
    assert '"tool_invocations": 1' in response.text
    assert "Scaling Beyond PMF" in response.text
    assert "Building Great Products" in response.text

    history = client.get(f"/api/v1/sessions/{session_id}").json()
    last_msg = history["messages"][-1]
    assert last_msg["message_metadata"]["tool_invocations"] == 1
    assert len(last_msg["message_metadata"]["sources"]) == 2
    assert last_msg["message_metadata"]["sources"][1]["title"] == "Scaling Beyond PMF"


def test_pi_extra_args_enables_custom_tools_and_disables_builtins():
    from app.agent import _pi_extra_args
    args = _pi_extra_args()
    assert "--no-builtin-tools" in args
    assert "--no-tools" not in args
    assert "--extension" in args
    ext_idx = args.index("--extension")
    assert "lenny_rag.ts" in args[ext_idx + 1]


def test_source_merging_deduplicates_chunks_without_losing_distinct_evidence():
    from app.main import _merge_tool_sources

    target = [dict(FAKE_SOURCE)]
    duplicate_source = dict(FAKE_SOURCE)
    duplicate_source["distance"] = 0.05  # slightly different distance, but same chunk_id
    distinct_source = {
        "chunk_id": "chunk-distinct-3",
        "source_id": "episode-distinct",
        "source_type": "podcast",
        "title": "Distinct Growth Framework",
        "guest": "Casey Winters",
        "url": "https://example.com/distinct",
        "publish_date": "2025-03-01",
        "chunk_index": 2,
        "content": "Focus on the core loop before paid acquisition.",
        "distance": 0.15,
    }

    _merge_tool_sources(target, [duplicate_source, distinct_source])

    # Target should only have 2 elements: the original FAKE_SOURCE and distinct_source
    assert len(target) == 2
    assert target[0]["chunk_id"] == "chunk-1"
    assert target[1]["chunk_id"] == "chunk-distinct-3"
    assert target[1]["title"] == "Distinct Growth Framework"


def test_citation_to_source_mapping_consistency(monkeypatch):
    session_id = _new_session()
    tool_chunk = {
        "chunk_id": "chunk-tool-activation",
        "source_id": "rahul-vohra",
        "source_type": "podcast",
        "title": "Superhuman's secret to success | Rahul Vohra",
        "guest": "Rahul Vohra",
        "url": "https://www.youtube.com/watch?v=0igjSRZyX-w",
        "publish_date": "2025-03-23",
        "chunk_index": 67,
        "content": "focus all of your engineers on finding product market fit... not for example on activation, because you have humans doing activation for you.",
        "distance": 0.22,
    }

    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    def fake_stream(messages, on_tool_call=None, initial_sources=None):
        assert initial_sources is not None
        assert len(initial_sources) == 1
        assert initial_sources[0]["chunk_id"] == "chunk-1"
        if on_tool_call:
            on_tool_call("search_lenny_transcripts", {"query": "product market fit versus user activation"}, [tool_chunk])
        # Model returns claims citing [1] for pre-retrieved and [2] for tool-retrieved
        yield "Strong products solve user problems [1]. Rahul Vohra advised focusing engineers on PMF, not activation [2]."

    monkeypatch.setattr(main, "stream_reply", fake_stream)

    response = client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "message": "What did Rahul Vohra say about activation?"},
    )

    assert response.status_code == 200

    # Verify SSE done event payload matches metadata
    done_payload = None
    for line in response.text.split("\n"):
        if line.startswith("data:"):
            import json
            try:
                ev = json.loads(line[5:].strip())
                if ev.get("type") == "done":
                    done_payload = ev
            except Exception:
                pass
    assert done_payload is not None
    assert len(done_payload["sources"]) == 2
    assert done_payload["sources"][0]["chunk_id"] == "chunk-1"
    assert done_payload["sources"][1]["chunk_id"] == "chunk-tool-activation"

    history = client.get(f"/api/v1/sessions/{session_id}").json()
    last_msg = history["messages"][-1]
    sources = last_msg["message_metadata"]["sources"]

    # Verify source 1 maps to [1]
    assert sources[0]["chunk_id"] == "chunk-1"
    assert sources[0]["title"] == "Building Great Products"

    # Verify source 2 maps to [2]
    assert sources[1]["chunk_id"] == "chunk-tool-activation"
    assert "Rahul Vohra" in sources[1]["title"]
    assert sources[1]["guest"] == "Rahul Vohra"

    # Assert content matches grounded citations and every citation maps to a valid source index
    import re
    citations = re.findall(r"\[(\d+)\]", last_msg["content"])
    assert set(citations) == {"1", "2"}
    for cit in citations:
        idx = int(cit)
        assert 1 <= idx <= len(sources)
        assert sources[idx - 1] is not None



def test_internal_type_error_in_model_propagates_without_retrying(monkeypatch):
    session_id = _new_session()
    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    call_count = 0

    def buggy_stream(messages, on_tool_call=None, initial_sources=None):
        nonlocal call_count
        call_count += 1
        raise TypeError("Bug in model token decoding logic")

    monkeypatch.setattr(main, "stream_reply", buggy_stream)

    response = client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "message": "Trigger error"},
    )

    assert response.status_code == 200
    # SSE stream catches the exception and yields an error event
    assert '"type": "error"' in response.text
    # Critically, the callable was only invoked ONCE (no retry occurred)
    assert call_count == 1


def test_system_prompt_includes_tool_guidelines_and_grounding_rules():
    from app.main import _build_system_prompt
    prompt = _build_system_prompt([FAKE_SOURCE])
    assert "search_lenny_transcripts" in prompt
    assert "Retrieved evidence:" in prompt
    assert "Tool Usage Guidelines:" in prompt
    assert "Strict Concept Separation" in prompt


def test_merge_tool_sources_handles_malformed_and_logs_warning(caplog):
    import logging
    from app.main import _merge_tool_sources

    target = [dict(FAKE_SOURCE)]
    incoming = [
        "not a dict",  # TypeError
        {"chunk_id": "missing_required_keys", "distance": 0.5},  # KeyError for missing source_id/source_type
        {"chunk_id": "bad_dist", "distance": "invalid_num", "source_id": "s1", "source_type": "podcast", "title": "t", "chunk_index": 0, "content": "c"},  # ValueError
        {
            "chunk_id": "valid_extra",
            "source_id": "s2",
            "source_type": "podcast",
            "title": "Valid Extra",
            "chunk_index": 0,
            "content": "Valid content",
            "distance": 0.22,
        },
    ]

    with caplog.at_level(logging.WARNING):
        _merge_tool_sources(target, incoming)

    assert len(target) == 2
    assert target[1]["chunk_id"] == "valid_extra"
    assert any("tool_source_normalization_failed" in rec.message for rec in caplog.records)


def test_call_with_optional_tool_callback_signature_inspection():
    import pytest
    from app.main import _call_with_optional_tool_callback

    # Accepts on_tool_call and initial_sources
    def modern_func(msg, on_tool_call=None, initial_sources=None):
        return f"modern:{msg}:{on_tool_call is not None}:{initial_sources is not None}"

    assert _call_with_optional_tool_callback(
        modern_func,
        "hello",
        on_tool_call=lambda *a: None,
        initial_sources=[{"chunk_id": "1"}],
    ) == "modern:hello:True:True"

    # Legacy signature without on_tool_call or initial_sources
    def legacy_func(msg):
        return f"legacy:{msg}"

    assert _call_with_optional_tool_callback(
        legacy_func,
        "hello",
        on_tool_call=lambda *a: None,
        initial_sources=[{"chunk_id": "1"}],
    ) == "legacy:hello"

    # Internal TypeError is NOT suppressed
    def buggy_func(msg, on_tool_call=None, initial_sources=None):
        raise TypeError("internal bug inside model")

    with pytest.raises(TypeError, match="internal bug inside model"):
        _call_with_optional_tool_callback(buggy_func, "hello", on_tool_call=lambda *a: None)


def test_setup_logging_configures_root_and_lenny_logger():
    import logging
    from app.main import setup_logging

    # When uvicorn logger has handlers, they should be attached to root
    mock_handler = logging.StreamHandler()
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = [mock_handler]

    setup_logging()

    assert mock_handler in logging.root.handlers
    assert logging.getLogger("lenny").level == logging.INFO
    # Clean up mock handler
    uvicorn_logger.handlers.remove(mock_handler)
    if mock_handler in logging.root.handlers:
        logging.root.handlers.remove(mock_handler)


def test_stream_chat_ship30_logs_quality_and_passes_token_budget(monkeypatch, caplog):
    import logging
    session_id = _new_session()
    captured_kwargs = {}

    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    # 1100+ word essay draft with proper title, valid markdown, and citations
    full_essay_body = ("In Lenny's interviews, great products solve deep customer problems [1]. " * 120)
    full_essay = "# The Art of Product-Market Fit\n\n" + full_essay_body

    def fake_stream(messages, on_tool_call=None, initial_sources=None, num_predict=None):
        captured_kwargs["num_predict"] = num_predict
        tokens = [full_essay[:200], full_essay[200:600], full_essay[600:]]
        yield from tokens

    monkeypatch.setattr(main, "stream_reply", fake_stream)

    with caplog.at_level(logging.INFO, logger="lenny.latency"):
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "session_id": session_id,
                "message": "Write a Ship 30 for 30 essay about finding product-market fit",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    # Verified token budget for essay is higher than regular 384
    assert captured_kwargs.get("num_predict") == 2500

    # Verified ship30_stream_quality appears in logs with passed=True and issues=none
    quality_logs = [rec.message for rec in caplog.records if "ship30_stream_quality" in rec.message]
    assert len(quality_logs) == 1
    log_msg = quality_logs[0]
    assert "first_token_streamed=true" in log_msg
    assert "passed=True" in log_msg
    assert "issues=none" in log_msg
    assert f"session_id={session_id}" in log_msg


def test_stream_chat_ship30_logs_quality_issues_on_short_draft(monkeypatch, caplog):
    import logging
    session_id = _new_session()

    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    short_draft = "# Title\n\nA very short essay [1]."

    def fake_stream(messages, on_tool_call=None, initial_sources=None, num_predict=None):
        yield short_draft

    monkeypatch.setattr(main, "stream_reply", fake_stream)
    # The quality retry is deterministic in this unit test; do not call a live model.
    monkeypatch.setattr(main, "generate_reply", lambda messages, **kwargs: short_draft)

    with caplog.at_level(logging.INFO, logger="lenny.latency"):
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "session_id": session_id,
                "message": "Draft a 1,250-word essay about PMF",
            },
        )

    assert response.status_code == 200
    quality_logs = [rec.message for rec in caplog.records if "ship30_stream_quality" in rec.message]
    assert len(quality_logs) == 1
    log_msg = quality_logs[0]
    assert "passed=False" in log_msg
    assert "short_draft" in log_msg


def test_stream_chat_regular_chat_preserves_default_num_predict(monkeypatch, caplog):
    import logging
    session_id = _new_session()
    captured_kwargs = {}

    monkeypatch.setattr(main, "retrieve_chunks", lambda query, db, top_k: [FAKE_SOURCE])

    def fake_stream(messages, on_tool_call=None, initial_sources=None, num_predict=None):
        captured_kwargs["num_predict"] = num_predict
        yield "Regular answer [1]."

    monkeypatch.setattr(main, "stream_reply", fake_stream)

    with caplog.at_level(logging.INFO, logger="lenny.latency"):
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "session_id": session_id,
                "message": "What is product-market fit?",
            },
        )

    assert response.status_code == 200
    # Regular chat keeps default 384 tokens
    assert captured_kwargs.get("num_predict") == 384
    # No ship30 quality check logged for regular questions
    quality_logs = [rec.message for rec in caplog.records if "ship30_stream_quality" in rec.message]
    assert len(quality_logs) == 0
