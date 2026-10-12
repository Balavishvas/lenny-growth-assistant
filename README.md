# Lenny Growth Assistant

A local-first, evidence-grounded research workspace for exploring product, growth, and startup ideas in Lenny Rachitsky's podcast and newsletter corpus. Built as a Forward Deployed Engineer take-home assessment.

## Project status

The core research and writing workflows are implemented: grounded RAG chat, PostgreSQL + pgvector retrieval, local model integration, the Ship 30 for 30 writing workflow, and browser-based artifact editing/export.

The remaining submission work is **final verification and evidence capture**: run tests on the exact commit being submitted, manually verify the primary user journeys, record the camera-on demo, and add its shareable link. See [Known limitations](#known-limitations) and [docs/DEMO.md](docs/DEMO.md).

## Features

- **Grounded research chat:** retrieves transcript passages and supplies them to the model as evidence.
- **Source traceability:** returns source metadata and renders clickable source citations in the workspace.
- **Conversation history:** session and message persistence for continuing a research conversation.
- **Local-first inference:** supports an Ollama chat path; the optional Pi Coding Agent runtime requires separate installation and provider configuration.
- **Persistent storage:** PostgreSQL stores application data and pgvector enables transcript similarity search.
- **Transcript ingestion:** parses Markdown transcripts, chunks content with overlap, batches embeddings, and stores source metadata.
- **Retrieval evaluation:** deterministic Precision@K, Recall@K, and MRR helpers with tests.
- **Ship 30 for 30 writing workflow:** a dedicated topic composer invokes long-form essay instructions.
- **Research artifacts:** edit Markdown/HTML output, preview it in a sandboxed browser view, copy it, and export it. Drafts are browser-local rather than a server-side artifact repository.
- **Operational endpoints:** API and database health checks support local diagnosis.

## Architecture

```text
Browser research workspace
        │ HTTP / streaming chat
        ▼
FastAPI application ───── Session and message persistence
        │
        ├── Retrieval service ─── PostgreSQL + pgvector
        │                              ▲
        ├── Model/runtime adapter       │
        │       └── Ollama or configured Pi runtime
        │
        └── Ship 30 for 30 writing workflow
                    │
                    └── Browser-local artifact editor / preview / export

Ingestion CLI ── transcript parsing/chunking ── Nomic embeddings ── vector storage
```

| Component | Technology |
| --- | --- |
| API | Python, FastAPI |
| Database | PostgreSQL, pgvector |
| Local chat | Ollama with model configured in `.env` (e.g. `qwen2.5:3b`) |
| Optional agent runtime | Pi Coding Agent; requires Node.js, Pi CLI, and a configured provider |
| Embeddings | Ollama `nomic-embed-text` |
| Frontend | Static HTML, CSS, and JavaScript served by FastAPI |
| Writing/artifacts | Ship 30 for 30 skill and browser-based editor |

The frontend is served by FastAPI; a separate Node.js frontend build is not required. See [architecture and design decisions](docs/architecture.md).

## Quick start (Windows PowerShell)

### Prerequisites

- Python 3.11+
- PostgreSQL with the pgvector extension
- Ollama installed and running
- Git
- The permitted transcript corpus available locally (not committed to this repository)

### Install dependencies

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure your local database and other required values in `.env`. Keep real credentials private. Check `.env.example` and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the current required variables and setup details.

Pull the models required by your local configuration if they are not already installed:

```powershell
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

Use the model names and embedding dimensions specified in your environment. Changing the embedding model/dimension requires re-ingestion to keep the stored vectors compatible.

### Start the API

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open these local URLs while the server is running:

- App: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health
- Database health: http://127.0.0.1:8000/health/database

Make sure PostgreSQL and Ollama are running before testing the full RAG flow.

### Optional Pi Coding Agent runtime

The default local Ollama path is the simplest option for the demo. To use the optional Pi runtime, install a compatible Node.js and Pi CLI version, configure a supported model provider, and set `AGENT_RUNTIME=pi` in `.env`. Keep `AGENT_RUNTIME=ollama` unless the Pi path has been explicitly configured and smoke-tested. A visible runtime option is not proof every provider is working.

### Ingest the transcript corpus

Place permitted transcript files in the configured `TRANSCRIPT_DIR` (default: `data-source/episodes`), then run:

```powershell
$env:PYTHONPATH = "backend"
python -m app.ingest_cli
```

The transcript corpus, database backups, embeddings, model files, and secrets should not be committed to Git. Ensure you have permission to use the corpus and follow the source repository's terms.

## Testing

Run the test suite from the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest -q
```

Re-run tests on the exact final commit before submission and report the actual output, date, and commit SHA. Historical test results are not a substitute for verifying the submitted version. Some checks may require a running PostgreSQL instance.

## Main workflow

1. Start PostgreSQL, Ollama, and the FastAPI application.
2. Open the research workspace and ask a question covered by the indexed corpus.
3. Inspect the answer and source references; open a source to review its evidence.
4. Ask a follow-up in the same conversation.
5. Test an unsupported question and verify the system handles missing evidence honestly.
6. Open **Ship30 essay**, enter a prepared topic, and generate a draft.
7. Inspect citations and quality warnings, then edit/preview the artifact and test copy/export.

See [docs/DEMO.md](docs/DEMO.md) for the 2–3 minute camera-on demo run sheet.

## Final submission checklist

- [ ] Run the full test suite on the exact final commit and record the output.
- [ ] Smoke-test health endpoints, grounded chat, source references, and unsupported-question behavior.
- [ ] Test Ship30 essay generation and review citation/quality warnings.
- [ ] Test artifact editing, preview, copy, and export.
- [ ] If using Pi or any optional provider, verify it separately; otherwise demonstrate the tested Ollama path.
- [ ] Confirm `.env`, API keys, transcript dumps, database backups, and generated model artifacts are not committed.
- [ ] Review `git status --short`, recent commits, and the final commit SHA.
- [ ] Record the 2–3 minute camera-on demo and add the shareable video link to the submission materials.

## Documentation

- [Product requirements](docs/PRD.md)
- [Architecture and design decisions](docs/architecture.md)
- [Frontend behavior](docs/frontend.md)
- [Development and local setup](docs/DEVELOPMENT.md)
- [Demo recording and submission checklist](docs/DEMO.md)
- [Engineering decisions, experiments, and known limitations](docs/DECISIONS_AND_LOG.md)

## Known limitations

- Retrieval metric helpers have deterministic unit tests, but a curated benchmark of real corpus queries and expected relevant source IDs has not been reported.
- Artifact drafts are stored in browser localStorage rather than a durable server-side artifact service.
- Frontend end-to-end coverage is incomplete; manually verify provider/runtime switching, citation behavior, long-form generation, and exports on the final commit.
- Local operation depends on PostgreSQL/pgvector and Ollama. Docker Compose is not required for the documented local workflow.
- Long-form output quality and citation formatting can vary; do not claim they are fully validated unless the exact final version passes the relevant checks.

## Assessment principles

1. Ground claims in retrieved evidence and expose traceable sources.
2. Prefer transparent uncertainty to confident unsupported answers.
3. Separate deterministic application logic from model behavior.
4. Test successful and failure paths, distinguishing unit tests from end-to-end verification.
5. Explain trade-offs and known limitations honestly so another engineer can operate and extend the system.
