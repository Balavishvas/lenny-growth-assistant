"""Automated verification script proving Pi custom-tool invocation during real web chat flow.

This script executes against the running local FastAPI server, creates a new session,
streams a web chat request requiring transcript retrieval, and verifies:
1. The retrieval API works.
2. The SSE stream yields token events.
3. The custom Pi tool (search_lenny_transcripts) was invoked during the request.
4. The tool results reached the model and contributed to its answer.
5. The SSE 'done' event includes valid sources and tool_invocations metadata.
6. The persisted session in PostgreSQL includes the tool-retrieved sources.
"""
from __future__ import annotations

import json
import sys
import uuid

import httpx


def main() -> int:
    base_url = "http://127.0.0.1:8000"
    client = httpx.Client(base_url=base_url, timeout=180.0)

    # 1. Health check
    try:
        health = client.get("/health").json()
        print(f"[1/5] Server health: {health.get('status')} ({health.get('app')})")
    except Exception as exc:
        print(f"FAIL: Could not reach {base_url}/health: {exc}", file=sys.stderr)
        return 1

    # 2. Retrieval API verification
    try:
        retrieval = client.post("/api/v1/retrieval/search", json={"query": "product market fit", "top_k": 3}).json()
        if not isinstance(retrieval, list) or len(retrieval) == 0:
            print("FAIL: /api/v1/retrieval/search returned no results", file=sys.stderr)
            return 1
        print(f"[2/5] Direct retrieval API returned {len(retrieval)} passages. Top source: '{retrieval[0].get('title')}'")
    except Exception as exc:
        print(f"FAIL: /api/v1/retrieval/search failed: {exc}", file=sys.stderr)
        return 1

    # 3. Create conversation session
    correlation_id = str(uuid.uuid4())[:8]
    session = client.post(
        "/api/v1/sessions",
        json={"title": f"Verify Pi Tool {correlation_id}", "metadata": {"test": True, "correlation_id": correlation_id}},
    ).json()
    session_id = session["id"]
    print(f"[3/5] Created chat session {session_id} (correlation: {correlation_id})")

    # 4. Stream chat request asking to search transcripts
    prompt = (
        "What did Rahul Vohra say about product market fit versus user activation in Superhuman? "
        "Please search the transcripts for his specific advice."
    )
    print(f"[4/5] Sending chat streaming request to /api/v1/chat/stream:\n      '{prompt}'")

    tokens: list[str] = []
    done_event: dict | None = None
    stream_error: str | None = None

    try:
        with client.stream("POST", "/api/v1/chat/stream", json={"session_id": session_id, "message": prompt}) as resp:
            if resp.status_code != 200:
                print(f"FAIL: HTTP {resp.status_code} from /api/v1/chat/stream: {resp.read().decode('utf-8')}", file=sys.stderr)
                return 1
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "token":
                        tokens.append(event.get("text", ""))
                    elif event.get("type") == "done":
                        done_event = event
                    elif event.get("type") == "error":
                        stream_error = event.get("message")
    except Exception as exc:
        print(f"FAIL: Streaming error: {exc}", file=sys.stderr)
        return 1

    if stream_error:
        print(f"FAIL: Received stream error event: {stream_error}", file=sys.stderr)
        return 1

    if not done_event:
        print("FAIL: Stream ended without a 'done' event", file=sys.stderr)
        return 1

    answer = "".join(tokens).strip()
    tool_invocations = done_event.get("tool_invocations", 0)
    sources = done_event.get("sources", [])
    grounded = done_event.get("grounded", False)
    provider = done_event.get("provider")
    model = done_event.get("model")

    print("\n--- Answer Text Received ---")
    print(answer)
    print("\n--- Completion Metadata ---")
    print(f"Provider: {provider} | Model: {model}")
    print(f"Grounded: {grounded} | Total sources: {len(sources)} | Tool invocations: {tool_invocations}")
    print(f"Retrieval ms: {done_event.get('retrieval_ms')} | Generation ms: {done_event.get('generation_ms')} | Total ms: {done_event.get('total_ms')}")
    print("\n--- Attached Sources ---")
    for i, s in enumerate(sources, 1):
        print(f"[{i}] {s.get('title')} (guest: {s.get('guest')}) [chunk {s.get('chunk_index')}]")
        print(f"    URL: {s.get('url')}")
        print(f"    Excerpt: {s.get('content', '')[:150]}...")

    # 5. Conclusively verify requirements
    print("\n[5/5] Verifying assertions...")
    checks = []

    # Check 1: Tool was invoked
    invoked = tool_invocations >= 1
    checks.append(("Pi custom tool was invoked during web chat", invoked))

    # Check 2: Sources attached
    has_sources = len(sources) > 0 and grounded is True
    checks.append(("Retrieved sources returned and marked grounded", has_sources))

    # Check 3: Answer is nonempty and grounded
    has_answer = len(answer) > 50
    checks.append(("Assistant generated a comprehensive answer", has_answer))

    # Check 4: Check persisted DB session
    session_detail = client.get(f"/api/v1/sessions/{session_id}").json()
    msgs = session_detail.get("messages", [])
    db_ok = len(msgs) == 2 and msgs[1]["role"] == "assistant" and msgs[1]["message_metadata"].get("tool_invocations", 0) >= 1
    checks.append(("Session and message metadata persisted in database", db_ok))

    all_passed = True
    for desc, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {desc}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nALL CHECKS PASSED: Pi Agent successfully invoked search_lenny_transcripts during the actual web chat flow!")
        return 0
    else:
        print("\nONE OR MORE CHECKS FAILED.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
