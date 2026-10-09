"""Command-line entry point for indexing local podcast transcripts."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.ingestion import ingest_transcripts


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Index Lenny podcast transcripts into PostgreSQL + pgvector.")
    parser.add_argument(
        "--source-dir",
        default=settings.transcript_dir,
        help="Directory containing guest folders with transcript.md files.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = ingest_transcripts(Path(args.source_dir), db)
    finally:
        db.close()

    print("Transcript ingestion complete")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
