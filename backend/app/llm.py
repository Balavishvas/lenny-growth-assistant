"""Small Ollama adapter for local chat completion."""

import json
from collections.abc import Iterator

import httpx

from app.config import get_settings


def generate_reply(messages: list[dict[str, str]]) -> str:
    """Send conversation messages to the configured local Ollama model."""
    settings = get_settings()
    if settings.llm_provider.lower() != "ollama":
        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    response = httpx.post(
        url,
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.ollama_keep_alive,
            "options": {"num_predict": settings.llm_num_predict},
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    answer = payload.get("message", {}).get("content", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned an empty response")
    return answer.strip()


def stream_reply(messages: list[dict[str, str]]) -> Iterator[str]:
    """Yield generated text chunks from Ollama's newline-delimited streaming response."""
    settings = get_settings()
    if settings.llm_provider.lower() != "ollama":
        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    with httpx.stream(
        "POST",
        url,
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "stream": True,
            "keep_alive": settings.ollama_keep_alive,
            "options": {"num_predict": settings.llm_num_predict},
        },
        timeout=settings.llm_timeout_seconds,
    ) as response:
        response.raise_for_status()
        yielded = False
        for line in response.iter_lines():
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = payload.get("message", {}).get("content", "")
            if isinstance(content, str) and content:
                yielded = True
                yield content
            if payload.get("done"):
                break
        if not yielded:
            raise ValueError("Ollama returned an empty response")
