"""Small Ollama adapter for local chat completion."""

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
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    answer = payload.get("message", {}).get("content", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned an empty response")
    return answer.strip()
