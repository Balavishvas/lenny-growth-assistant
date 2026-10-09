# Lenny Growth Assistant

A grounded AI assistant for exploring ideas from Lenny Rachitsky's podcast and newsletter content. The project is being built as a take-home assessment for a Forward Deployed Engineer role.

> **Status:** Foundation/design phase. Runtime behavior and integrations are not implemented yet.

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
- **Local inference:** Ollama (initially testing qwen2.5:3b and qwen2.5:7b)
- **Agent runtime:** Pi Coding Agent integration, subject to a compatibility spike
- **Retrieval:** transcript ingestion, chunking, embeddings, retrieval, and source attribution
- **Frontend:** chat UI with a side-by-side artifact viewer
- **Operations:** Docker Compose, environment-based configuration, tests, and structured logging

The agent runtime is intentionally a validation item: Pi's SDK is TypeScript-oriented while the required API is FastAPI/Python. The implementation will choose and document a reliable integration boundary instead of assuming the two runtimes interoperate directly.

## Project documents

- [Product requirements (PRD)](docs/PRD.md)
- [Architecture and key decisions](docs/architecture.md)

## Development status

- [x] Public repository created
- [ ] PRD and architecture reviewed
- [ ] FastAPI health endpoint and configuration
- [ ] PostgreSQL sessions and message persistence
- [ ] Transcript ingestion and retrieval with citations
- [ ] Agent orchestration and provider switching
- [ ] Ship 30 for 30 writing skill
- [ ] Artifact generation and isolated viewer
- [ ] Frontend
- [ ] Automated tests and manual UI test plan
- [ ] Docker Compose and handoff documentation
- [ ] Demo recording

## Local development

The exact one-command setup will be documented once the initial application skeleton and Docker configuration are in place. Do not commit API keys, local environment files, transcript content you do not have rights to redistribute, or other secrets.

## Assessment principles

1. Ground claims in retrieved evidence and expose sources.
2. Separate orchestration, retrieval, provider configuration, persistence, and presentation.
3. Validate model and agent-runtime compatibility early.
4. Test failure paths, not only the happy path.
5. Keep the implementation explainable and operable.
