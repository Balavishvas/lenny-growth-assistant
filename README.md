# Lenny Growth Assistant

A grounded AI assistant for exploring ideas from Lenny Rachitsky's podcast and newsletter content. This is a take-home assessment project for a Forward Deployed Engineer role.

> **Status:** Initial documentation and FastAPI health-check slice committed. Chat, persistence, retrieval, agent integration, and UI are still planned.

## Product goals

- Answer growth, product, and startup questions using retrieved source material rather than unsupported guesses.
- Show traceable sources for answers and acknowledge when the available content does not support a conclusion.
- Keep chat sessions and message history isolated and persisted.
- Support a configurable local Ollama model and a configurable cloud model provider.
- Generate useful writing artifacts, including a Ship 30 for 30-style essay, and display artifacts beside the conversation.
- Be runnable and testable with clear setup instructions, structured logs, and graceful failure handling.

## Planned stack

- **API:** Python + FastAPI
- **Persistence:** PostgreSQL
- **Local inference:** Ollama (testing qwen2.5:3b and qwen2.5:7b)
- **Agent runtime:** Pi Coding Agent integration, subject to a compatibility spike
- **Retrieval:** transcript ingestion, chunking, embeddings, retrieval, and source attribution
- **Frontend:** chat UI with a side-by-side artifact viewer
- **Operations:** Docker Compose, environment-based configuration, tests, and structured logging

Pi's SDK is TypeScript-oriented while the required API is FastAPI/Python. We will validate the integration boundary before treating it as a final design decision.

## Project documents

- [Product requirements (PRD)](docs/PRD.md)
- [Architecture and key decisions](docs/architecture.md)
- [Local development and testing](docs/DEVELOPMENT.md)

## Current status

- [x] Public repository created
- [x] PRD and architecture documentation
- [x] Environment settings and safe example configuration
- [x] FastAPI health endpoint and smoke test
- [ ] PostgreSQL sessions and message persistence
- [ ] Transcript ingestion and retrieval with citations
- [ ] Agent orchestration and provider switching
- [ ] Ship 30 for 30 writing skill
- [ ] Artifact generation and isolated viewer
- [ ] Frontend
- [ ] Automated tests and manual UI test plan
- [ ] Docker Compose and handoff documentation
- [ ] Demo recording

## Quick start

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for complete setup and test instructions.

In short, from the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload
```

Then visit http://127.0.0.1:8000/health and http://127.0.0.1:8000/docs.

The current health endpoint checks API liveness only; it does not yet verify PostgreSQL or Ollama readiness.

## Assessment principles

1. Ground claims in retrieved evidence and expose sources.
2. Separate orchestration, retrieval, provider configuration, persistence, and presentation.
3. Validate model and agent-runtime compatibility early.
4. Test failure paths, not only the happy path.
5. Keep the implementation explainable and operable.

Do not commit real credentials, local `.env` files, or source material unless redistribution is permitted.
