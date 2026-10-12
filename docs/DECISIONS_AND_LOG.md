# Implementation Decisions, Experiments, and Known Limitations

This is a concise engineering log for the assessment. It records decisions and observed results that are known from the repository and development notes; it is not a fabricated timestamp-by-timestamp terminal transcript. Add dated entries with exact commands/output when performing new experiments.

## Design decisions

### Local-first inference
**Decision:** Use Ollama for the primary demo and keep model/provider selection behind a small backend boundary.

**Why:** The app can be exercised without requiring a paid cloud API key, and the developer can inspect the full local retrieval flow.

**Trade-off:** Local model latency, memory usage, and answer quality depend on the model and hardware. A provider switch is not evidence that every provider/model combination has been tested.

### PostgreSQL + pgvector
**Decision:** Store session/message data and embedded transcript chunks in PostgreSQL, using pgvector for similarity search.

**Why:** One local service covers relational persistence and vector retrieval, reducing infrastructure for a take-home project.

**Trade-off:** Local setup requires PostgreSQL and a working pgvector extension. Cosine distance is a ranking signal, not a calibrated probability that an answer is correct.

### Separate ingestion, retrieval metrics, and generation
**Decision:** Keep transcript ingestion/chunking and vector search separate from answer generation; add deterministic Precision@K, Recall@K, and MRR helpers with unit tests.

**Why:** Retrieval calculations can be tested deterministically and the corpus can be re-indexed without changing the generation layer.

**Trade-off:** Unit tests for metric formulas do not demonstrate retrieval quality on a real corpus. A fixed query-to-relevant-source benchmark is still needed.

### Conditional Ship 30 for 30 writing skill
**Decision:** Load long-form writing instructions for explicit essay requests rather than every normal chat message. Provide a dedicated in-app topic composer.

**Why:** The workflow is easier to discover while keeping ordinary research chat focused.

**Trade-off:** Long output and citation formatting need end-to-end validation. A quality checker warning must be treated as a real limitation, not hidden or described as resolved without a passing reproduction.

### Browser-local artifact editing
**Decision:** Provide editable Markdown/HTML drafts, preview, copy, and export in the frontend.

**Why:** This enables a useful research-to-writing workflow without adding a separate artifact-storage service.

**Trade-off:** Drafts are browser-local rather than a server-side artifact system. Browser-local state is not a substitute for multi-user persistence or backup.

## Experiments and verification status

| Area | Evidence available | Status / caveat |
| --- | --- | --- |
| Python tests | A previous user-reported run completed with **54 passed, 1 deprecation warning**. | Re-run against the exact final commit and record the fresh output before submission. |
| Database | Previous development notes report `GET /health/database` returned HTTP 200. | Recheck if the local environment or schema changed. |
| Retrieval + local generation | Development notes describe local Ollama, PostgreSQL/pgvector, Pi runtime, and streamed essay generation being exercised. | Treat as a prior manual run, not an automated end-to-end guarantee for every commit. |
| Essay generation | One observed run produced a 1,279-word draft after retrieving five sources. | The essay checker reported `missing_citations`; do not claim citation validation is fully passing until fixed and re-tested. |
| Retrieval evaluation | Precision@K, Recall@K, and MRR helpers have deterministic unit tests. | No curated real-corpus benchmark result is claimed. |
| Cloud provider | An optional Anthropic route exists in the code. | Only claim it works if tested with a valid key and the exact current commit. Never commit or paste the key into logs. |
| UI | A dedicated Ship30 topic composer, artifact editor, source view, and provider selector are present in the current branch. | Perform the manual browser checklist in `docs/DEMO.md`; automated end-to-end UI coverage is incomplete. |

## Known limitations and next improvements

1. **Citation quality:** a previously observed essay run failed the citation checker with `missing_citations`. Verify the citation format from generation through validation and rendering before claiming the issue is fixed.
2. **Corpus evaluation:** metric helpers exist, but there is no published, curated evaluation set with expected relevant chunk/source IDs and corpus-level scores.
3. **Frontend end-to-end coverage:** browser flows such as provider switching, long essay generation, source navigation, and artifact export still require manual checks.
4. **Artifact persistence:** editing state is stored in browser localStorage; it is not a durable, account-level server artifact store.
5. **Provider compatibility:** each provider/model combination needs a direct smoke test; a visible selector alone is not proof of successful operation.
6. **Runtime environment:** local development depends on PostgreSQL/pgvector and Ollama; the project does not claim a fully hosted, one-click deployment.

## Coding-agent / development transcript note

The repository commit history records code changes and their commit messages. This file records the decisions and verification facts currently available. It is **not** a verbatim prompt/response transcript or a full terminal log. If the assessment explicitly requires the actual coding-agent conversation transcript, export the real transcript from the tool used and add it separately; do not reconstruct dialogue and label it as original.

For reproducible verification, capture the following on the final branch and include the exact output in the submission notes:

```powershell
$env:PYTHONPATH = "backend"
.\venv\Scripts\python.exe -m pytest -q
git status --short
git log -10 --oneline --decorate
git rev-parse HEAD
```

Record the date, commit SHA, test count, warnings, and any failed checks. Never claim a command passed unless you actually ran it on the recorded commit.
