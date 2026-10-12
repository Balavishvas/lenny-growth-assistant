# Demo and Submission Guide

This guide is the run sheet for a **2–3 minute, camera-on walkthrough**. Keep the demo focused on one end-to-end user journey; do not try to show every endpoint.

## Before recording

1. Pull the assessment branch and run the documented tests.
2. Start PostgreSQL with pgvector, Ollama, and the FastAPI application. Confirm `/health` and `/health/database` respond successfully.
3. Confirm the transcript corpus is already indexed. Do not run a full ingestion during the recording.
4. Open the app at `http://127.0.0.1:8000/` and `/docs` in separate tabs. Close unrelated tabs and notifications.
5. Use the local Ollama provider for the main flow so the demo does not depend on a paid API or network availability. Only show the cloud-provider option if a valid key is already configured and tested.
6. Preselect a short, answerable question you have already verified against the corpus. Have a separate unsupported question ready to demonstrate the no-evidence behavior.
7. Do a timed rehearsal. Keep a backup terminal ready in case the UI needs a refresh. Never show API keys, local credentials, or private transcript files.

## 2–3 minute recording script

| Time | What to show | What to say |
| --- | --- | --- |
| 0:00–0:20 | Camera on; show the app and project name | “This is Lenny Growth Assistant, a research workspace for asking questions over an indexed podcast/newsletter corpus. The main design goal is that answers should expose their evidence rather than sound confident without support.” |
| 0:20–0:55 | Ask one pretested, corpus-answerable question | Explain that the request flows through FastAPI, retrieval uses PostgreSQL/pgvector, and the model receives retrieved passages. Point at the answer and source references. |
| 0:55–1:15 | Open a source/citation; ask one short follow-up | Show provenance and conversational continuity. Describe only behavior you can visibly verify. |
| 1:15–1:40 | Ask a question known to be outside the corpus | Show the transparent insufficient-evidence response, if the current indexed corpus produces it. Do not stage or claim a successful no-answer result if it does not occur. |
| 1:40–2:15 | Click **Ship30 essay**, enter a prepared topic, generate, inspect result | Explain that this is a dedicated long-form writing workflow and that grounding/citation quality is checked. Be honest if word count or citation validation warns; do not present an unverified essay as fully sourced. |
| 2:15–2:40 | Show artifact editor/preview or export, then briefly show tests/docs | Explain that the artifact can be edited and exported from the browser. Mention the test result you actually observed and the main limitation still documented. |
| 2:40–3:00 | Return to camera / project README | Summarize the main trade-off: local inference and explicit source visibility improve control/privacy, while small local models and citation formatting remain areas to validate. |

If you need to shorten the recording, prioritize one grounded answer with sources, the writing workflow, and a quick mention of testing/limitations. Do not speed through the UI.

## Recording quality checklist

- [ ] Camera is on and face is visible at the start and end.
- [ ] Voice is clear; app text is readable at 100% zoom.
- [ ] No notifications, passwords, API keys, or private files are visible.
- [ ] One successful run was rehearsed immediately before recording.
- [ ] The demo stays within 2–3 minutes.
- [ ] Claims match the visible behavior and the documented limitations.
- [ ] The video is uploaded to the submission location and the link is added to the README or submission note.

## Submission evidence

Record the actual results rather than filling these in from memory:

- Commit/branch demonstrated: `feat/ship30-writing-workflow` at `<record the final SHA>`
- Test command: `$env:PYTHONPATH = "backend"; python -m pytest -q`
- Test result: `<paste exact output and date>`
- Manual checks: `<chat/source citation, unsupported query, essay, artifact/export, provider if tested>`
- Demo video: `<insert final shareable link>`
- Known issues: cite `docs/DECISIONS_AND_LOG.md` and the limitations section in the README.

Do not publish credentials, copyrighted corpus dumps, or database contents as demo artifacts.
