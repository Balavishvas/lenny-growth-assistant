"""Pi Coding Agent adapter with a local Ollama fallback."""
from __future__ import annotations

from collections.abc import Callable, Iterator
import json
import logging
import os
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.llm import generate_reply, stream_reply

logger = logging.getLogger("lenny.agent")

_tool_invocations: list[dict[str, Any]] = []


def get_tool_invocations() -> list[dict[str, Any]]:
    """Return recorded tool invocations (for verification and tests)."""
    return list(_tool_invocations)


def reset_tool_invocations() -> None:
    """Reset recorded tool invocations."""
    _tool_invocations.clear()


def _record_tool_invocation(tool_name: str, args: dict, result_count: int = 0) -> None:
    _tool_invocations.append({
        "tool_name": tool_name,
        "args": args,
        "result_count": result_count,
    })


def _to_prompt(messages: list[dict[str, str]]) -> str:
    """Pass the grounded system prompt and bounded chat history to Pi."""
    sections = []
    for message in messages:
        role = message.get("role", "user").upper()
        sections.append(f"## {role}\n{message.get('content', '')}")
    return "\n\n".join(sections)


def _pi_extra_args() -> list[str]:
    """Load the custom retrieval tool while keeping Pi built-in CLI tools disabled."""
    extension = Path(__file__).resolve().parent / "pi_extensions" / "lenny_rag.ts"
    return [
        "--no-builtin-tools",
        "--no-skills",
        "--no-context-files",
        "--extension",
        str(extension),
    ]


def _pi_env(existing_sources: list[dict] | None = None, num_predict: int | None = None, num_ctx: int | None = None) -> dict[str, str]:
    """Ensure the custom extension knows the API URL and existing source citation indices."""
    env = dict(os.environ)
    if "LENNY_API_BASE_URL" not in env:
        env["LENNY_API_BASE_URL"] = "http://127.0.0.1:8000"
    if num_predict is not None:
        env["LENNY_NUM_PREDICT"] = str(num_predict)
    if num_ctx is not None:
        env["LENNY_NUM_CTX"] = str(num_ctx)
    if existing_sources:
        mapping = {str(s["chunk_id"]): i + 1 for i, s in enumerate(existing_sources) if "chunk_id" in s}
        env["LENNY_EXISTING_SOURCES"] = json.dumps(mapping)
        env["LENNY_SOURCE_OFFSET"] = str(len(existing_sources))
    else:
        env["LENNY_EXISTING_SOURCES"] = "{}"
        env["LENNY_SOURCE_OFFSET"] = "0"
    return env


def generate_agent_reply(
    messages: list[dict[str, str]],
    on_tool_call: Callable[[str, dict, list[dict]], None] | None = None,
    initial_sources: list[dict] | None = None,
    num_predict: int | None = None,
    num_ctx: int | None = None,
) -> str:
    """Use Pi Coding Agent when selected; retain native Ollama as a fallback."""
    settings = get_settings()
    runtime = settings.agent_runtime.lower().strip()
    logger.info("agent_runtime_selected runtime=%s model=%s", runtime, settings.ollama_model)
    if runtime in {"ollama", "native"}:
        return generate_reply(messages, num_predict=num_predict, num_ctx=num_ctx)
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
        logger.info("pi_agent_starting extension=%s", Path(__file__).resolve().parent / "pi_extensions" / "lenny_rag.ts")
        with PiClient(
            cwd=str(Path.cwd()),
            provider="ollama",
            model=settings.ollama_model,
            no_session=True,
            extra_args=_pi_extra_args(),
            env=_pi_env(initial_sources, num_predict=num_predict, num_ctx=num_ctx),
        ) as pi:
            answer_parts = []
            active_tool_calls: dict[str, dict] = {}
            with pi.stream(_to_prompt(messages)) as stream:
                for event in stream:
                    ev_type = getattr(event, "type", None)
                    raw = getattr(event, "raw", None) or {}
                    if ev_type == "tool_execution_start":
                        t_name = raw.get("toolName", "unknown")
                        t_call_id = raw.get("toolCallId") or "default"
                        t_args = raw.get("args") or {}
                        active_tool_calls[t_call_id] = t_args
                        logger.info("custom_tool_execution_started tool=%s query=%s", t_name, t_args.get("query"))
                    elif ev_type == "tool_execution_end":
                        t_name = raw.get("toolName", "unknown")
                        t_call_id = raw.get("toolCallId") or "default"
                        t_args = active_tool_calls.pop(t_call_id, None) or raw.get("args") or {}
                        t_res = raw.get("result") or {}
                        t_details = t_res.get("details") or {}
                        retrieved = t_details.get("sources") or []
                        is_err = raw.get("isError", False)
                        _record_tool_invocation(t_name, t_args, len(retrieved))
                        logger.info(
                            "custom_tool_execution_completed tool=%s query=%s results=%d is_error=%s duration_ms=%s",
                            t_name,
                            t_args.get("query"),
                            len(retrieved),
                            is_err,
                            raw.get("durationMs"),
                        )
                        if on_tool_call:
                            on_tool_call(t_name, t_args, retrieved)
                    delta = getattr(event, "text_delta", None)
                    if isinstance(delta, str) and delta:
                        answer_parts.append(delta)
                result = stream.result()
            answer = "".join(answer_parts).strip() or getattr(result, "text", "").strip()
    except Exception:
        logger.exception("pi_agent_failed")
        raise RuntimeError(
            "Pi agent failed. Verify Node.js, the Pi CLI, and its configured local model."
        ) from None
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Pi agent returned an empty response")
    logger.info("pi_agent_completed response_chars=%d", len(answer.strip()))
    return answer.strip()


def stream_agent_reply(
    messages: list[dict[str, str]],
    on_tool_call: Callable[[str, dict, list[dict]], None] | None = None,
    initial_sources: list[dict] | None = None,
    num_predict: int | None = None,
    num_ctx: int | None = None,
) -> Iterator[str]:
    """Stream output from the selected runtime while preserving the SSE token contract."""
    settings = get_settings()
    runtime = settings.agent_runtime.lower().strip()
    logger.info("agent_runtime_selected runtime=%s model=%s streaming=true", runtime, settings.ollama_model)
    if runtime in {"ollama", "native"}:
        yield from stream_reply(messages, num_predict=num_predict, num_ctx=num_ctx)
        return
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
        logger.info("pi_agent_starting extension=%s", Path(__file__).resolve().parent / "pi_extensions" / "lenny_rag.ts")
        with PiClient(
            cwd=str(Path.cwd()),
            provider="ollama",
            model=settings.ollama_model,
            no_session=True,
            extra_args=_pi_extra_args(),
            env=_pi_env(initial_sources),
        ) as pi:
            active_tool_calls: dict[str, dict] = {}
            with pi.stream(_to_prompt(messages)) as stream:
                for event in stream:
                    ev_type = getattr(event, "type", None)
                    raw = getattr(event, "raw", None) or {}
                    if ev_type == "tool_execution_start":
                        t_name = raw.get("toolName", "unknown")
                        t_call_id = raw.get("toolCallId") or "default"
                        t_args = raw.get("args") or {}
                        active_tool_calls[t_call_id] = t_args
                        logger.info("custom_tool_execution_started tool=%s query=%s", t_name, t_args.get("query"))
                    elif ev_type == "tool_execution_end":
                        t_name = raw.get("toolName", "unknown")
                        t_call_id = raw.get("toolCallId") or "default"
                        t_args = active_tool_calls.pop(t_call_id, None) or raw.get("args") or {}
                        t_res = raw.get("result") or {}
                        t_details = t_res.get("details") or {}
                        retrieved = t_details.get("sources") or []
                        is_err = raw.get("isError", False)
                        _record_tool_invocation(t_name, t_args, len(retrieved))
                        logger.info(
                            "custom_tool_execution_completed tool=%s query=%s results=%d is_error=%s duration_ms=%s",
                            t_name,
                            t_args.get("query"),
                            len(retrieved),
                            is_err,
                            raw.get("durationMs"),
                        )
                        if on_tool_call:
                            on_tool_call(t_name, t_args, retrieved)
                    delta = getattr(event, "text_delta", None)
                    if isinstance(delta, str) and delta:
                        yield delta
                result = stream.result()
    except Exception:
        logger.exception("pi_agent_failed")
        raise RuntimeError(
            "Pi agent failed. Verify Node.js, the Pi CLI, and its configured local model."
        ) from None
    if not getattr(result, "text", "").strip():
        raise ValueError("Pi agent returned an empty response")
    logger.info("pi_agent_completed response_chars=%d streaming=true", len(result.text.strip()))
