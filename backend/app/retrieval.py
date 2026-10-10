"""Vector similarity retrieval with source metadata preserved for citations."""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.config import get_settings
from app.embeddings import embed_texts
from app.knowledge_models import DocumentChunk

logger = logging.getLogger("lenny.retrieval")


def retrieve_chunks(query: str, db: Session, top_k: int | None = None) -> list[dict]:
    """Return the most similar transcript chunks for a natural-language query."""
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    settings = get_settings()
    limit = top_k if top_k is not None else settings.retrieval_top_k
    if limit < 1 or limit > 20:
        raise ValueError("top_k must be between 1 and 20")

    embedding_started = time.perf_counter()
    query_vector = embed_texts([query.strip()], input_type="query")[0]
    embedding_ms = (time.perf_counter() - embedding_started) * 1000

    search_started = time.perf_counter()
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    rows = (
        db.query(DocumentChunk, distance.label("distance"))
        .order_by(distance)
        .limit(limit)
        .all()
    )
    db_search_ms = (time.perf_counter() - search_started) * 1000
    logger.info(
        "retrieval_breakdown embedding_ms=%.2f db_search_ms=%.2f total_ms=%.2f top_k=%d results=%d",
        embedding_ms,
        db_search_ms,
        embedding_ms + db_search_ms,
        limit,
        len(rows),
    )

    results = []
    for chunk, cosine_distance in rows:
        results.append(
            {
                "chunk_id": chunk.id,
                "source_id": chunk.source_id,
                "source_type": chunk.source_type,
                "title": chunk.title,
                "guest": chunk.guest,
                "url": chunk.source_url,
                "publish_date": chunk.publish_date,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "distance": float(cosine_distance),
            }
        )
    return results
