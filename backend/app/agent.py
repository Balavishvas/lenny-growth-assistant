"""Agent-runtime adapter for Lenny Growth Assistant.

The Pi runtime is optional so the local Ollama demo remains usable without
Node/Pi installed. Set AGENT_RUNTIME=pi to route responses through Pi's runtime;
retrieval and database writes remain deterministic application code.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from app.config import get_settings
from app.llm import generate_reply, stream_reply


def _to_prompt(messages: list[dict[str, str]]) -> str:
    """Convert grounded chat messages into a single agent task."""
    sections: list[str] = []
    for message in messages:
        role = message.get("role", "user").upper()
        content = message.get("content", "")
        sections.append(f"## {role}\n{content}")
    return (
        "You are Lenny Growth Assistant. Follow the system instructions and use only "
        "the supplied retrieved evidence for claims about Lenny's content. Preserve "
        "citation markers included in the evidence prompt. Do not invent sources.\n\n"
        + "\n\n".join(sections)
    )


def generate_agent_reply(messages: list[dict[str, str]]) -> str:
    """Run Pi when selected, otherwise preserve the local Ollama adapter."""
    settings = get_settings()
    runtime = settings.agent_runtime.lower().strip()
    if runtime in {"ollama", "native"}:
        return generate_reply(messages)
    if runtime != "pi":
        raise RuntimeError(f"Unsupported agent runtime: {runtime}")

    try:
        from pi_agent import PiClient
    except ImportError as exc:
        raise RuntimeError(
            "Pi runtime selected but pi-agent-python-sdk is missing. Install requirements "
            "and configure Pi, or set AGENT_RUNTIME=ollama."
        ) from exc

    try:
        with PiClient(cwd=str(Path.cwd()), no_session=True) as pi:
            result = pi.run(_to_prompt(messages))
    except Exception as exc:
        raise RuntimeError(
            "Pi agent failed. Verify the Pi CLI installation and configured model provider."
        ) from exc
    answer = getattr(result, "text", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Pi agent returned an empty response")
    return answer.strip()


def stream_agent_reply(messages: list[dict[str, str]]) -> Iterator[str]:
    """Stream Ollama responses; chunk Pi's final response to preserve the SSE contract."""
    settings = get_settings()
    if settings.agent_runtime.lower().strip() in {"ollama", "native"}:
        yield from stream_reply(messages)
        return
    answer = generate_agent_reply(messages)
    for offset in range(0, len(answer), 48):
        yield answer[offset : offset + 48]
