# Lenny Growth Assistant

A grounded AI assistant for exploring ideas from Lenny Rachitsky's podcast and newsletter content. This is a take-home assessment project for a Forward Deployed Engineer role.

## Current implementation

- FastAPI API with health checks, session creation/history, message persistence, and local Ollama chat.
- PostgreSQL persistence and pgvector-backed transcript chunk storage.
- Local Ollama embedding adapter using Nomic Embed Text (768-dimensional vectors by default).
- Markdown transcript parsing, overlapping chunking, batched embeddings, repeatable ingestion, and source metadata.
- Vector similarity search exposed through `POST /api/v1/retrieval/search`.
- RAG-powered chat that supplies retrieved passages to the local model, returns traceable source chunks, persists source metadata, and uses an honest fallback when retrieval finds no passages.
- Responsive research workspace UI with conversation history, Markdown answer rendering, clickable source citations, and a side-by-side artifact editor/preview.
- Dedicated Ship 30 for 30 writing workflow with conditional essay instructions and quality checks.
- Deterministic retrieval metric helpers for Precision@K, Recall@K, and MRR, with unit tests.

## Architecture

- **API:** Python + FastAPI
- **Persistence:** PostgreSQL + pgvector
- **Agent orchestration:** selectable Pi Coding Agent runtime through `pi-agent-python-sdk`, with a native Ollama fallback for local development
- **Local chat model:** Ollama `qwen2.5:3b` (override via `.env`)
- **Local embedding model:** Ollama `nomic-embed-text`
- **Retrieval:** transcript ingestion, chunking, vector similarity search, and source attribution
- **Frontend:** static HTML/CSS/JavaScript served by FastAPI at `/`; no Node.js build step required
- **Artifacts:** browser-local editable Markdown/HTML drafts with sandboxed HTML preview and export
- **Writing workflow:** `backend/app/skills/ship_30_for_30.md` is conditionally loaded by `backend/app/writing_skill.py` for explicit long-form essay requests.

## Quick start

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for complete setup and testing instructions.

From the repository root in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload
```

Index your local transcript corpus:

```powershell
python -m app.ingest_cli
```

To use Pi Coding Agent, install Node.js 22.19+ and Pi CLI 0.85.1+ (`npm install -g @earendil-works/pi-coding-agent@0.87.1`), configure a local Ollama-compatible model in Pi, install requirements, then set `AGENT_RUNTIME=pi` in `.env`. Start with `AGENT_RUNTIME=ollama` until the Pi CLI is configured and verified.

The external transcript corpus is intentionally excluded from Git. Download it locally and ensure you comply with the source repository's terms. Never commit your `.env` file or real credentials.

## Test RAG chat

Create a session with `POST /api/v1/sessions`, then send a message to `POST /api/v1/chat` using the returned `session_id`. The response includes an `answer`, a `grounded` flag, and a `sources` array containing the passages supplied to the model. If retrieval returns no passages, the API returns a transparent fallback instead of asking the model to guess.

## Tests

Run the deterministic unit suite from the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest -q
```

The retrieval metric helpers are in `backend/app/retrieval_eval.py`; tests in `tests/test_retrieval_eval.py` cover ranking metrics and edge cases. These tests verify metric calculations, **not** retrieval quality on the real transcript corpus. A corpus-level benchmark still requires a curated fixed set of queries and relevant chunk/source identifiers.

## Next milestones

- [ ] Add a curated fixed query/expected-source benchmark and run it against the indexed transcript corpus.
- [ ] Add server-side artifact persistence and comprehensive frontend end-to-end tests.
- [ ] Add provider controls, Docker Compose, handoff documentation, and demo recording.

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
