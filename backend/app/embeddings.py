"""Ollama embedding adapter with explicit document/query task prefixes."""

from __future__ import annotations

import httpx

from app.config import get_settings


def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Generate embeddings locally through Ollama.

    Nomic retrieval inputs use search_document: for indexed passages and
    search_query: for user questions. The prefixes are sent to Ollama but are
    not stored in the source text.
    """
    if input_type not in {"document", "query"}:
        raise ValueError("input_type must be 'document' or 'query'")
    if not texts:
        return []

    settings = get_settings()
    if settings.embedding_provider.lower() != "ollama":
        raise RuntimeError(f"Unsupported embedding provider: {settings.embedding_provider}")

    prefix = "search_query: " if input_type == "query" else "search_document: "
    inputs = [text if text.startswith(prefix) else f"{prefix}{text}" for text in texts]
    url = f"{settings.ollama_base_url.rstrip('/')}/api/embed"
    embeddings: list[list[float]] = []

    batch_size = max(1, settings.embedding_batch_size)
    with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
        for offset in range(0, len(inputs), batch_size):
            batch = inputs[offset : offset + batch_size]
            response = client.post(
                url,
                json={"model": settings.embedding_model, "input": batch},
            )
            response.raise_for_status()
            payload = response.json()
            batch_embeddings = payload.get("embeddings")
            if not isinstance(batch_embeddings, list) or len(batch_embeddings) != len(batch):
                raise ValueError("Ollama returned an unexpected embedding response")

            for vector in batch_embeddings:
                if not isinstance(vector, list) or len(vector) != settings.embedding_dimensions:
                    actual = len(vector) if isinstance(vector, list) else "unknown"
                    raise ValueError(
                        f"Embedding dimension mismatch: expected {settings.embedding_dimensions}, got {actual}"
                    )
                embeddings.append([float(value) for value in vector])

    return embeddings
