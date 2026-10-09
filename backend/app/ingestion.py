"""Repeatable transcript ingestion into PostgreSQL + pgvector."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.chunking import chunk_text, parse_transcript
from app.config import get_settings
from app.embeddings import embed_texts
from app.knowledge_models import DocumentChunk


def _content_hash(source_id: str, chunk_index: int, content: str) -> str:
    value = f"{source_id}\0{chunk_index}\0{content}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def ingest_transcripts(source_dir: Path, db: Session) -> dict[str, int]:
    """Index all transcript.md files under source_dir, replacing each source atomically."""
    settings = get_settings()
    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Transcript directory not found: {source_dir}")

    paths = sorted(source_dir.rglob("transcript.md"))
    stats = {"files_found": len(paths), "files_indexed": 0, "chunks_indexed": 0, "empty_files": 0}

    for path in paths:
        transcript = parse_transcript(path, source_dir)
        chunks = chunk_text(
            transcript.content,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        if not chunks:
            stats["empty_files"] += 1
            continue

        vectors = embed_texts(chunks, input_type="document")
        if len(vectors) != len(chunks):
            raise ValueError(f"Embedding count mismatch for {path}")

        records: list[dict[str, Any]] = []
        for index, (content, vector) in enumerate(zip(chunks, vectors, strict=True)):
            records.append(
                {
                    "source_id": transcript.source_id,
                    "source_type": transcript.source_type,
                    "title": transcript.title,
                    "guest": transcript.guest,
                    "source_url": transcript.url,
                    "publish_date": transcript.publish_date,
                    "chunk_index": index,
                    "content": content,
                    "content_hash": _content_hash(transcript.source_id, index, content),
                    "source_metadata": {
                        "description": transcript.description,
                        "relative_path": path.relative_to(source_dir).as_posix(),
                    },
                    "embedding": vector,
                }
            )

        try:
            db.query(DocumentChunk).filter(
                DocumentChunk.source_id == transcript.source_id
            ).delete(synchronize_session=False)
            db.add_all([DocumentChunk(**record) for record in records])
            db.commit()
        except Exception:
            db.rollback()
            raise

        stats["files_indexed"] += 1
        stats["chunks_indexed"] += len(records)

    return stats
