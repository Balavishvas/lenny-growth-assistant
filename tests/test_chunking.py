"""Unit tests for transcript parsing and overlap-aware chunking."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.chunking import chunk_text, parse_transcript  # noqa: E402


def test_chunk_text_returns_empty_for_blank_input():
    assert chunk_text("   \n  ") == []


def test_chunk_text_respects_size_and_creates_overlap():
    text = " ".join(f"word{i}" for i in range(150))
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert any(set(left.split()) & set(right.split()) for left, right in zip(chunks, chunks[1:]))


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello world", chunk_size=10, overlap=10)


def test_parse_transcript_extracts_frontmatter_and_source_path(tmp_path):
    root = tmp_path / "episodes"
    transcript_path = root / "Jane Doe" / "transcript.md"
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text(
        "---\nguest: Jane Doe\ntitle: Building Great Products\nyoutube_url: https://example.com/episode\npublish_date: '2025-01-02'\n---\nTranscript body here.",
        encoding="utf-8",
    )

    parsed = parse_transcript(transcript_path, root)

    assert parsed.source_id == "Jane Doe"
    assert parsed.title == "Building Great Products"
    assert parsed.guest == "Jane Doe"
    assert parsed.url == "https://example.com/episode"
    assert parsed.publish_date == "2025-01-02"
    assert parsed.content == "Transcript body here."
