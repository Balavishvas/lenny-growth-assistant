# Development Guide

## Prerequisites

- Python 3.11 or newer
- Git
- PostgreSQL 18 with the pgvector extension available
- Ollama running locally
- Ollama models: `qwen2.5:7b` and `nomic-embed-text`
- Lenny transcript repository downloaded locally into `data-source/episodes/`

The transcript corpus is intentionally excluded from Git. Confirm that you have permission to use the downloaded source material and do not redistribute it from this repository.

## Set up a local environment

From the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `DATABASE_URL` to your local PostgreSQL password. Never commit `.env`.

Pull the local models if they are not already installed:

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

The API startup ensures the pgvector extension exists and creates the application's tables. The PostgreSQL role must have permission to create the extension, or an administrator must enable it once.

## Run the API

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload
```

Open:
- Liveness: http://127.0.0.1:8000/health
- Database readiness: http://127.0.0.1:8000/health/database
- Interactive API docs: http://127.0.0.1:8000/docs

## Index podcast transcripts

Place the transcript repository under `data-source/`, so episode files are available at `data-source/episodes/<guest>/transcript.md`.

Run this from the project root in a terminal with the virtual environment active:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingest_cli
```

For a different folder:

```powershell
python -m app.ingest_cli --source-dir "D:\path\to\episodes"
```

The command prints files discovered, files indexed, chunks indexed, and empty files. Each source is replaced in a transaction when re-indexed, so rerunning ingestion does not append duplicate chunks. Embeddings are generated in batches by the local Ollama model.

## Test retrieval

After ingestion, use Swagger at `/docs` or run:

```powershell
$body = @{ query = "How should an early-stage startup think about user retention?"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/retrieval/search" -Method Post -ContentType "application/json" -Body $body
```

Each result includes the chunk text, episode title, source URL where available, chunk index, and cosine distance. Lower cosine distance means a closer vector match; it is not a calibrated probability.

## Run tests

```powershell
$env:PYTHONPATH = "backend"
pytest -q
```

Chunking and frontmatter tests run without a live model or database. API tests currently use the configured PostgreSQL database, so ensure it is available before running the full suite.

## Important behavior and limitations

- Embeddings use Nomic's `search_document:` prefix for transcript passages and `search_query:` for user questions.
- The configured vector dimension defaults to 768 and is validated against every Ollama response.
- The current `/api/v1/retrieval/search` endpoint validates retrieval independently. The chat endpoint is not yet wired to retrieved evidence in this milestone.
- A model change that changes embedding dimensions or embedding space requires re-indexing the corpus.
- Do not commit local transcript files, `.env`, database credentials, or model artifacts.
