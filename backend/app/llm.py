"""Small Ollama adapter for local chat completion."""

import json
from collections.abc import Iterator

import httpx

from app.config import get_settings


def _anthropic_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system = "\n\n".join(item["content"] for item in messages if item.get("role") == "system")
    conversation = [
        {"role": item.get("role", "user"), "content": item.get("content", "")}
        for item in messages if item.get("role") in {"user", "assistant"}
    ]
    return system, conversation


def generate_reply(
    messages: list[dict[str, str]], num_predict: int | None = None,
    num_ctx: int | None = None, provider: str | None = None,
    api_key: str | None = None, model: str | None = None,
) -> str:
    """Generate via request-selected Anthropic Claude or configured local Ollama."""
    settings = get_settings()
    selected_provider = (provider or settings.llm_provider).lower().strip()
    if selected_provider == "anthropic":
        if not api_key or not api_key.strip():
            raise ValueError("Enter an Anthropic API key to use Claude.")
        system, conversation = _anthropic_messages(messages)
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key.strip(), "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model or "claude-sonnet-4-20250514", "max_tokens": num_predict or settings.llm_num_predict,
                  "system": system, "messages": conversation},
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        blocks = response.json().get("content", [])
        answer = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        if not answer.strip():
            raise ValueError("Claude returned an empty response")
        return answer.strip()
    if selected_provider != "ollama":
        raise RuntimeError(f"Unsupported LLM provider: {selected_provider}")

    predict_tokens = num_predict if num_predict is not None else settings.llm_num_predict
    options: dict[str, int] = {"num_predict": predict_tokens}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    response = httpx.post(
        url,
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "keep_alive": settings.ollama_keep_alive,
            "options": options,
        },
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    answer = payload.get("message", {}).get("content", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned an empty response")
    return answer.strip()


def stream_reply(
    messages: list[dict[str, str]], num_predict: int | None = None,
    num_ctx: int | None = None, provider: str | None = None,
    api_key: str | None = None, model: str | None = None,
) -> Iterator[str]:
    """Stream output from Claude or Ollama without persisting user-supplied API keys."""
    settings = get_settings()
    selected_provider = (provider or settings.llm_provider).lower().strip()
    if selected_provider == "anthropic":
        if not api_key or not api_key.strip():
            raise ValueError("Enter an Anthropic API key to use Claude.")
        system, conversation = _anthropic_messages(messages)
        with httpx.stream(
            "POST", "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key.strip(), "anthropic-version": "2023-06-01",
                     "content-type": "application/json", "accept": "text/event-stream"},
            json={"model": model or "claude-sonnet-4-20250514", "max_tokens": num_predict or settings.llm_num_predict,
                  "system": system, "messages": conversation, "stream": True},
            timeout=settings.llm_timeout_seconds,
        ) as response:
            response.raise_for_status()
            yielded = False
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {}).get("text", "")
                    if delta:
                        yielded = True
                        yield delta
                elif event.get("type") == "error":
                    raise RuntimeError("Anthropic returned a generation error.")
            if not yielded:
                raise ValueError("Claude returned an empty response")
        return
    if selected_provider != "ollama":
        raise RuntimeError(f"Unsupported LLM provider: {selected_provider}")

    predict_tokens = num_predict if num_predict is not None else settings.llm_num_predict
    options: dict[str, int] = {"num_predict": predict_tokens}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    with httpx.stream(
        "POST",
        url,
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "stream": True,
            "keep_alive": settings.ollama_keep_alive,
            "options": options,
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
