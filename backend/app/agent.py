"""Pi Coding Agent adapter with a local Ollama fallback."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from app.config import get_settings
from app.llm import generate_reply, stream_reply


def _to_prompt(messages: list[dict[str, str]]) -> str:
    """Pass the grounded system prompt and bounded chat history to Pi."""
    sections = []
    for message in messages:
        role = message.get("role", "user").upper()
        sections.append(f"## {role}\n{message.get('content', '')}")
    return "\n\n".join(sections)


def _pi_extra_args() -> list[str]:
    """Load only the app-specific retrieval tool, keeping Pi built-in tools disabled."""
    extension = Path(__file__).resolve().parent / "pi_extensions" / "lenny_rag.ts"
    return [
        "--no-tools",
        "--no-skills",
        "--no-context-files",
        "--extension",
        str(extension),
    ]


def generate_agent_reply(messages: list[dict[str, str]]) -> str:
    """Use Pi Coding Agent when selected; retain native Ollama as a fallback."""
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
            "Pi runtime selected but pi-agent-python-sdk is not installed. "
            "Install requirements and configure the Pi CLI, or set AGENT_RUNTIME=ollama."
        ) from exc

    try:
        with PiClient(
            cwd=str(Path.cwd()),
            provider="ollama",
            model=settings.ollama_model,
            no_session=True,
            extra_args=_pi_extra_args(),
        ) as pi:
            result = pi.run(_to_prompt(messages))
    except Exception as exc:
        raise RuntimeError(
            "Pi agent failed. Verify Node.js, the Pi CLI, and its configured local model."
        ) from exc
    answer = getattr(result, "text", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Pi agent returned an empty response")
    return answer.strip()


def stream_agent_reply(messages: list[dict[str, str]]) -> Iterator[str]:
    """Stream output from the selected runtime while preserving the SSE token contract."""
    settings = get_settings()
    if settings.agent_runtime.lower().strip() in {"ollama", "native"}:
        yield from stream_reply(messages)
        return

    try:
        from pi_agent import PiClient
    except ImportError as exc:
        raise RuntimeError(
            "Pi runtime selected but pi-agent-python-sdk is not installed. "
            "Install requirements and configure the Pi CLI, or set AGENT_RUNTIME=ollama."
        ) from exc

    try:
        with PiClient(
            cwd=str(Path.cwd()),
            provider="ollama",
            model=settings.ollama_model,
            no_session=True,
            extra_args=_pi_extra_args(),
        ) as pi:
            with pi.stream(_to_prompt(messages)) as stream:
                for event in stream:
                    delta = getattr(event, "text_delta", None)
                    if isinstance(delta, str) and delta:
                        yield delta
                result = stream.result()
    except Exception as exc:
        raise RuntimeError(
            "Pi agent failed. Verify Node.js, the Pi CLI, and its configured local model."
        ) from exc
    if not getattr(result, "text", "").strip():
        raise ValueError("Pi agent returned an empty response")
