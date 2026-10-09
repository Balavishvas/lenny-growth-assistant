# Development Guide

## Prerequisites

- Python 3.11 or newer
- Git
- Ollama for local-model testing (not required for the health endpoint)
- PostgreSQL will be required when persistence is implemented

## Set up a local environment

From the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

The current health endpoint does not connect to PostgreSQL or Ollama yet. The example environment file is a configuration template; the database service and model adapter will be implemented in later steps.

## Run the API

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload
```

Then open:
- Health: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

Expected health response includes `"status": "ok"`. This is a liveness check only; it does not yet prove database or model readiness.

## Run tests

From the repository root:

```powershell
pytest -q
```

The first test covers the initial health endpoint. More tests will be added with session persistence, retrieval, provider routing, and artifact handling.

## Current implementation boundary

Implemented:
- Typed environment settings loaded from environment variables and an optional local `.env` file.
- FastAPI app metadata and `GET /health`.
- A smoke test for the health endpoint.
- Product requirements and architecture documents.

Not implemented yet:
- Database connection, migrations, and persisted sessions/messages.
- Transcript ingestion, embeddings, retrieval, and citations.
- Agent runtime integration and provider switching.
- Chat endpoints, frontend, artifact storage/viewer, Docker Compose, and end-to-end tests.

Keep local secrets in `.env`; it is ignored by Git. Never commit API keys or source material unless redistribution is permitted.
