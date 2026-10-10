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
- Tests for transcript chunking/parsing, chat grounding, source persistence, and unsupported-question fallback.

## Architecture

- **API:** Python + FastAPI
- **Persistence:** PostgreSQL + pgvector
- **Agent orchestration:** selectable Pi Coding Agent runtime through `pi-agent-python-sdk`, with a native Ollama fallback for local development\n- **Local chat model:** Ollama `qwen2.5:3b` (override via `.env`)
- **Local embedding model:** Ollama `nomic-embed-text`
- **Retrieval:** transcript ingestion, chunking, vector similarity search, and source attribution
- **Frontend:** static HTML/CSS/JavaScript served by FastAPI at `/`; no Node.js build step required
- **Artifacts:** browser-local editable Markdown/HTML drafts with sandboxed HTML preview and export
- **Agent:** `AGENT_RUNTIME=pi` routes grounded chat through Pi Coding Agent; `AGENT_RUNTIME=ollama` retains the native Ollama adapter. Pi requires Node.js and a configured Pi CLI model provider.\n- **Ship 30 writing skill / server-side artifact persistence:** remaining milestones

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

To use Pi Coding Agent, install Node.js 22.19+ and Pi CLI 0.85.1+ (`npm install -g @earendil-works/pi-coding-agent@0.87.1`), configure a local Ollama-compatible model in Pi, install requirements, then set `AGENT_RUNTIME=pi` in `.env`. Start with `AGENT_RUNTIME=ollama` until the Pi CLI is configured and verified.\n\nThe external transcript corpus is intentionally excluded from Git. Download it locally and ensure you comply with the source repository's terms. Never commit your `.env` file or real credentials.

## Test RAG chat

Create a session with `POST /api/v1/sessions`, then send a message to `POST /api/v1/chat` using the returned `session_id`. The response includes an `answer`, a `grounded` flag, and a `sources` array containing the passages supplied to the model. If retrieval returns no passages, the API returns a transparent fallback instead of asking the model to guess.

## Next milestones

- [ ] Add retrieval evaluation with a fixed query/expected-source set (Recall@K, MRR, Precision@K).
- [ ] Implement the dedicated Ship 30 for 30 writing skill and stronger artifact-generation flow.
- [ ] Add server-side artifact persistence and comprehensive frontend end-to-end tests.
- [ ] Add provider controls, Docker Compose, handoff documentation, and demo recording.
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
