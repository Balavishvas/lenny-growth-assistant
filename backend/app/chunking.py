"""Parse transcript Markdown and split it into traceable overlapping chunks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Transcript:
    source_id: str
    title: str
    guest: str | None
    url: str | None
    publish_date: str | None
    description: str | None
    source_type: str
    content: str


def parse_transcript(path: Path, source_root: Path) -> Transcript:
    """Parse YAML frontmatter and body from a transcript Markdown file."""
    raw = path.read_text(encoding="utf-8-sig").strip()
    metadata: dict[str, Any] = {}

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            parsed = yaml.safe_load(parts[1]) or {}
            if isinstance(parsed, dict):
                metadata = parsed
            raw = parts[2].strip()

    relative = path.resolve().relative_to(source_root.resolve())
    source_id = relative.parent.as_posix()
    title = str(metadata.get("title") or metadata.get("guest") or relative.parent.name)
    guest_value = metadata.get("guest")
    guest = str(guest_value).strip() if guest_value else None
    url_value = metadata.get("youtube_url") or metadata.get("url")
    url = str(url_value).strip() if url_value else None

    published = metadata.get("publish_date")
    if isinstance(published, (date, datetime)):
        published = published.isoformat()
    publish_date = str(published).strip() if published else None
    description_value = metadata.get("description")
    description = str(description_value).strip() if description_value else None

    return Transcript(
        source_id=source_id,
        title=title,
        guest=guest,
        url=url,
        publish_date=publish_date,
        description=description,
        source_type="podcast",
        content=raw,
    )


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Split text into overlapping character windows, preferring word boundaries."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    length = len(cleaned)

    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            boundary = cleaned.rfind(" ", start + int(chunk_size * 0.7), end)
            if boundary > start:
                end = boundary

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break

        next_start = max(start + 1, end - overlap)
        # Avoid beginning the next chunk in the middle of a word.
        next_space = cleaned.find(" ", next_start, min(next_start + 40, length))
        start = next_space + 1 if next_space != -1 else next_start

    return chunks
