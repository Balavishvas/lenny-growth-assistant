# Lenny Growth Assistant

A local-first, evidence-grounded research workspace for exploring product, growth, and startup ideas in Lenny Rachitsky's podcast/newsletter corpus. Built as a Forward Deployed Engineer take-home assessment.

> **Assessment status:** Core research chat, retrieval, the Ship 30 for 30 writing workflow, and browser-local artifact editing are implemented. The remaining work is final-commit verification, the camera-on demo, and submission evidence. See [Known limitations and verification](docs/DECISIONS_AND_LOG.md) for caveats; do not treat a UI control as proof that every provider or output-quality path passes end-to-end checks.

## What it does

- **Research chat:** ask questions through FastAPI and use retrieved transcript passages as evidence.
- **Source traceability:** return source metadata with retrieved passages and show source references in the workspace.
- **Local-first model path:** use Ollama for local generation and Nomic Embed Text for embeddings.
- **Persistent data:** PostgreSQL stores application data; pgvector supports transcript-vector similarity search.
- **Writing workflow:** a dedicated Ship 30 for 30 topic composer invokes long-form essay instructions for explicit essay requests.
- **Research artifacts:** edit assistant output as Markdown/HTML, preview it in the browser, copy it, and export it as a file. Drafts are browser-local, not a server-side artifact repository.
- **Retrieval evaluation primitives:** deterministic Precision@K, Recall@K, and MRR helpers with unit tests.

## Architecture at a glance

```text
Browser UI (HTML / CSS / JavaScript)
        │ same-origin HTTP + streaming chat
        ▼
FastAPI application ───── Session / message persistence
        │                              │
        ├── Retrieval service ─── PostgreSQL + pgvector
        │                              ▲
        ├── Model/runtime adapter      │
        │       └── Ollama / configured agent runtime
        │
        └── Writing-skill routing ─── Ship 30 for 30 instructions

Ingestion CLI ── transcript parsing/chunking ── embeddings ── vector storage
```

The frontend is served by FastAPI; a separate Node.js frontend build is not required. See [Architecture and design decisions](docs/architecture.md) for boundaries and trade-offs.

## Quick start (PowerShell)

### Prerequisites

- Python 3.11+
- PostgreSQL with the pgvector extension
- Ollama running locally
- Git
- The permitted transcript corpus available locally (not committed to this repository)

### Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your local database connection. Use placeholders in shared documentation; never commit real credentials. Confirm PostgreSQL is running and the pgvector extension is available.

Pull the models configured for your local environment if needed:

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

Check `.env.example` and `docs/DEVELOPMENT.md` before changing model names or embedding dimensions. The embedding model/dimension must match the vectors already stored; changing embedding spaces requires re-ingestion.

### Start the API

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open:
- App: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health
- Database health: http://127.0.0.1:8000/health/database

If the repository is checked out into a virtual environment named `venv`, use `.\venv\Scripts\python.exe` or activate that environment first.

### Ingest transcripts

Place allowed transcript files in the configured `TRANSCRIPT_DIR` (default: `data-source/episodes`). Then run:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingest_cli
```

The corpus is intentionally excluded from Git. Confirm you have permission to use the source material and comply with the source repository's terms. Do not commit transcript dumps, generated embeddings, database backups, or model artifacts.

## Tests

Run the test suite from the repository root with the environment active:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest -q
```

Test results are commit-specific. Run the full suite against the exact commit you submit, then record the actual output, date, and commit SHA in your submission notes. Do not treat an earlier passing run as verification of a later commit.

## How to try the main workflow

1. Start the backend and open the research workspace.
2. Ask a short question that you know is covered by the indexed corpus.
3. Inspect the returned source references and open a source card.
4. Ask a follow-up in the same conversation.
5. Use **Ship30 essay**, enter a topic, and generate a long-form draft.
6. Inspect citations, word count, and any quality-check result; report warnings honestly.
7. Open the artifact editor, review the preview, and test copy/export.

See [Demo and submission guide](docs/DEMO.md) for the camera-on recording run sheet.

## Implementation status

### Completed

- [x] FastAPI backend, session/message persistence, and local Ollama chat.
- [x] PostgreSQL + pgvector transcript storage, ingestion, embeddings, and similarity retrieval.
- [x] RAG chat with source attribution and a transparent no-evidence fallback.
- [x] Retrieval metric helpers for Precision@K, Recall@K, and MRR, with unit tests.
- [x] Dedicated Ship 30 for 30 writing workflow.
- [x] Research artifact editor with preview, copy, and export.
- [x] Core development, architecture, frontend, decision-log, and demo documentation.

### Final submission checklist

- [ ] Re-run the complete test suite on the exact commit being submitted; capture the output and SHA.
- [ ] Manually smoke-test normal chat, source references, unsupported questions, Ship30 essay generation, and artifact export.
- [ ] Verify the writing workflow's citation/quality checks on the final code and document any remaining warnings.
- [ ] Record the 2–3 minute camera-on demo and add the shareable video link.
- [ ] Review `git status`, recent commits, and the repository for secrets, local data, or generated artifacts before submission.

## Documentation

- [Product requirements (PRD)](docs/PRD.md)
- [Architecture and design decisions](docs/architecture.md)
- [Frontend behavior](docs/frontend.md)
- [Development and local setup](docs/DEVELOPMENT.md)
- [Demo recording and submission checklist](docs/DEMO.md)
- [Engineering decisions, experiments, and known limitations](docs/DECISIONS_AND_LOG.md)

## Known limitations

- Retrieval metric helpers have deterministic unit tests, but a curated benchmark of real corpus queries and expected relevant chunk/source IDs has not been reported.
- Artifact drafts are stored in browser localStorage rather than a durable server-side artifact service.
- Frontend end-to-end coverage is incomplete; provider switching, citation behavior, long-form writing, and exports still require manual verification.
- Local operation depends on PostgreSQL/pgvector and Ollama. A visible cloud-provider selector does not mean every cloud route has been validated.
- Long-form generation latency and citation quality can vary by model, topic, and local hardware; report results from the exact final build rather than assuming quality from the presence of the workflow.

## Assessment principles

1. Ground corpus claims in retrieved evidence and expose provenance.
2. Prefer transparent uncertainty to confident unsupported answers.
3. Separate deterministic application logic from model behavior.
4. Test both successful and failure paths; distinguish unit tests from end-to-end evidence.
5. Explain trade-offs and limitations honestly rather than overstating completeness.
