# Lenny Growth Assistant

A grounded AI assistant for exploring ideas from Lenny Rachitsky's podcast and newsletter content. This is a take-home assessment project for a Forward Deployed Engineer role.

## Current implementation

- FastAPI API with health checks, session creation/history, message persistence, and local Ollama chat.
- PostgreSQL persistence and pgvector-backed transcript chunk storage.
- Local Ollama embedding adapter using Nomic Embed Text (768-dimensional vectors by default).
- Markdown transcript parsing, overlapping chunking, batched embeddings, repeatable ingestion, and source metadata.
- Vector similarity search exposed through `POST /api/v1/retrieval/search`.
- Unit tests for transcript frontmatter parsing and chunking.

## Architecture

- **API:** Python + FastAPI
- **Persistence:** PostgreSQL + pgvector
- **Local chat model:** Ollama `qwen2.5:7b`
- **Local embedding model:** Ollama `nomic-embed-text`
- **Retrieval:** transcript ingestion, chunking, vector similarity search, and source attribution
- **Frontend / agent / artifacts:** subsequent milestones

## Quick start

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for complete setup and testing instructions.

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload
```

Index your local transcript corpus:

```powershell
python -m app.ingest_cli
```

The external transcript corpus is intentionally excluded from Git. Download it locally and ensure you comply with the source repository's terms. Never commit your `.env` file or real credentials.

## Next milestones

- [ ] Connect retrieval to chat with evidence-grounded answers and citations.
- [ ] Add retrieval evaluation with a fixed query/expected-source set (Recall@K, MRR, Precision@K).
- [ ] Implement the dedicated Ship 30 for 30 writing skill.
- [ ] Add artifact generation and isolated side-by-side viewer.
- [ ] Build the frontend, provider controls, and comprehensive end-to-end tests.
- [ ] Docker Compose, handoff documentation, and demo recording.

## Project documents

- [Product requirements](docs/PRD.md)
- [Architecture and design decisions](docs/architecture.md)
- [Development guide](docs/DEVELOPMENT.md)

## Assessment principles

1. Ground claims in retrieved evidence and expose traceable sources.
2. Keep orchestration, retrieval, provider configuration, persistence, and presentation separate.
3. Evaluate retrieval quality rather than relying on anecdotal examples.
4. Test failure paths as well as the happy path.
5. Keep the implementation explainable and operable.
