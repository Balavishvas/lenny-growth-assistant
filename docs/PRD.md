# Product Requirements Document (PRD)

## 1. Product summary

**Lenny Growth Assistant** is a conversational research assistant for questions about product management, growth, startups, and related ideas covered in Lenny Rachitsky's podcast and newsletter material. Its defining behavior is evidence-grounded answers: retrieve relevant source passages, cite them, preserve conversation context, and be candid when the available corpus does not support an answer.

This document describes the intended product behavior for the take-home assessment. It does not claim that features are implemented yet.

## 2. Problem and opportunity

A user exploring a large body of interviews and essays needs more than a generic chatbot. They need to find relevant ideas quickly, understand where an answer came from, ask follow-up questions, and turn research into a useful deliverable without losing context.

A fluent answer that is not supported by the source material is a product failure. Source traceability, uncertainty handling, and a usable workflow are core requirements rather than optional polish.

## 3. Target users and key jobs

### Primary user
A product builder, founder, growth practitioner, or researcher exploring product and startup questions.

### Jobs to be done
- Ask a question in natural language and receive a concise, useful answer grounded in the indexed corpus.
- Inspect the sources supporting important claims.
- Ask follow-up questions without restating all prior context.
- Learn when the corpus has insufficient evidence rather than receiving a fabricated answer.
- Turn a conversation into a structured written artifact.
- Return to previous sessions and continue work.

## 4. Product principles

1. **Evidence before eloquence:** retrieved passages should support factual claims about the corpus.
2. **Visible provenance:** make source metadata available with answers.
3. **Honest uncertainty:** explicitly say when evidence is missing, weak, or conflicting.
4. **User control:** expose model-provider selection without code edits.
5. **Continuity:** persist independent sessions and message history.
6. **Useful output:** support both conversational answers and editable/exportable artifacts.
7. **Operational clarity:** errors should be actionable and logs should aid debugging without leaking secrets.

## 5. Functional requirements

### FR-1: Chat and sessions
- Users can create a session and send messages within it.
- Each session has a stable ID and timestamps.
- Sessions are isolated; messages from one session must not leak into another.
- Conversation history is persisted and can be retrieved after a restart.
- User metadata may be associated with a session where available; authentication requirements must be stated explicitly rather than implied.

### FR-2: Source corpus ingestion
- Ingest permitted Lenny podcast/newsletter transcript or article material from supported input files or configured sources.
- Normalize text and preserve source identity, title, URL when available, publication/episode metadata when available, and chunk location.
- Split content into retrieval-sized chunks with metadata attached.
- Provide an explicit refresh/re-ingestion path that avoids accidental duplication.
- Do not commit copyrighted source dumps to the public repository unless redistribution rights are confirmed.

### FR-3: Grounded retrieval and answers
- Retrieve relevant chunks for a user query and use them as evidence for the response.
- Return source references with answers so the user can inspect provenance.
- Preserve relevant conversational context for follow-up questions.
- If retrieval returns no useful evidence, say so and avoid presenting unsupported corpus claims as facts.
- Retrieval, answer generation, and source formatting should be independently testable.

### FR-4: Agent orchestration
- Use the selected agent runtime to coordinate model interactions and registered tools.
- Give the agent a clear tool contract for corpus search and artifact creation.
- Keep deterministic work (input validation, database writes, health checks, provider configuration validation) in ordinary application code where practical.
- Validate the selected runtime against the local Ollama model before relying on it in the end-to-end flow.
- Record the integration boundary and any compatibility limitations in the architecture documentation.

### FR-5: Model provider configuration
- Support a local Ollama model for the demo.
- Allow a cloud provider to be configured as an alternative.
- Switching providers must be possible through environment/configuration or a visible UI setting, not source-code edits.
- Do not require cloud credentials for the local-model demo.
- Missing keys, unsupported models, connection failures, and timeouts must produce clear errors without exposing secrets.

### FR-6: Ship 30 for 30 writing skill
- Provide a dedicated writing workflow/skill for an approximately 1,250-word essay.
- The essay should have a strong hook, coherent narrative, useful headings, selective bullets and bold emphasis, and a clear practical takeaway.
- Claims that purport to summarize Lenny's source material must remain grounded in retrieved evidence.
- The skill should guide structure and quality without inventing citations or pretending unsupported claims are sourced.

### FR-7: Artifacts
- Users can ask the assistant to create a Markdown or HTML/CSS artifact from the conversation.
- Artifacts are displayed in a dedicated viewer beside the chat.
- Generated artifacts have identifiable type, content, and creation/update timestamps.
- Treat generated HTML as untrusted: sanitize it and/or render it in a strongly isolated sandbox with a restrictive policy. Never directly execute arbitrary generated scripts in the main application origin.

### FR-8: Reliability and operations
- Provide a health endpoint and structured application logs.
- Handle database unavailability, empty retrieval, model timeouts, missing provider credentials, and Ollama being offline gracefully.
- Provide an example environment file with placeholders only.
- Provide one-command local startup where practical, preferably with Docker Compose.
- Document setup, configuration, tests, limitations, and handoff steps.

## 6. UX requirements

- The main workflow is a chat interface with clear loading, empty, success, and error states.
- Source references should be easy to distinguish from assistant prose and should expose meaningful metadata.
- The provider selection must be visible and understandable; show which provider/model is active.
- The artifact viewer should not obscure the conversation and should support reading long content.
- Empty or weak retrieval must not look like a confident, fully sourced answer.
- Manual UI testing must cover narrow and wide viewports, long answers, source lists, provider errors, and artifact rendering.

## 7. Non-functional requirements

- **Security:** no committed secrets; validate inputs; isolate untrusted HTML; use parameterized database operations/ORM; avoid logging tokens or sensitive message content unnecessarily.
- **Maintainability:** separate API, persistence, retrieval, provider adapter, agent orchestration, and UI responsibilities.
- **Testability:** unit tests for retrieval and provider routing; API tests; persistence/session-isolation tests; a documented manual UI test plan.
- **Observability:** structured logs with request/session correlation where practical; actionable errors.
- **Portability:** documented local setup and environment-based configuration.
- **Grounding quality:** evaluation cases should include answerable, ambiguous, and unsupported questions.

## 8. Out of scope for the initial assessment

- Production multi-tenant authentication and enterprise authorization unless specifically required by the final implementation.
- Training a custom foundation model.
- Guaranteed factual correctness beyond the quality and coverage of the available corpus.
- Publishing copyrighted source material without permission.
- Arbitrary execution of generated code or HTML.
- A promise that all cloud providers are interchangeable without provider-specific adaptation.

## 9. Acceptance criteria

1. A developer can configure and start the app using documented instructions and example environment variables.
2. A user can create separate sessions, send messages, and retrieve persisted history.
3. A supported corpus can be ingested, refreshed, searched, and traced to its source metadata.
4. Answers include source references when supported by retrieval and explicitly acknowledge insufficient evidence.
5. Local Ollama inference can be selected for the demo without cloud API credentials.
6. The provider can be changed through configuration or the UI without editing application source.
7. The writing workflow produces an approximately 1,250-word structured essay and does not fabricate source attribution.
8. Markdown/HTML artifacts can be viewed beside chat; HTML is treated as untrusted content.
9. Automated tests cover API behavior, retrieval, provider routing, and persistence/session isolation.
10. The repository includes architecture/design documentation, known limitations, failed attempts and corrections in the coding-agent transcript, a manual UI test plan, and a short demo video link.

## 10. Key risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Local model has limited context or answer quality | Start with a small evaluation set; adjust context and model only after measuring quality and memory use. |
| Agent runtime does not integrate cleanly with FastAPI | Run a compatibility spike early and document a narrow, testable integration boundary. |
| Corpus coverage is incomplete | Show source metadata, refresh status, and a clear insufficient-evidence response. |
| Generated HTML introduces security risk | Sanitize and isolate rendering; disable scripts and restrict resource loading. |
| Database or model is unavailable | Timeouts, graceful errors, health checks, and logs. |
| Source redistribution is not permitted | Keep source files outside the public repo and document ingestion instructions. |

## 11. Evaluation plan

Build a small, versioned set of representative questions:
- Answerable question with direct supporting passages.
- Question requiring synthesis across multiple passages.
- Follow-up that relies on prior conversation context.
- Unsupported question that should trigger an uncertainty response.
- Similar-sounding query where retrieval should distinguish sources.
- Provider unavailable or timeout scenario.
- Session isolation and history persistence scenario.

Track retrieval relevance and inspect generated answers and citations manually. Do not treat fluent output alone as evidence of success.
