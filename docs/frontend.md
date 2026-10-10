# Research Workspace Frontend

## Overview

The frontend is a dependency-free HTML, CSS, and JavaScript workspace served by FastAPI:

- `/` serves `frontend/index.html`.
- `/static/styles.css` serves the responsive dark research-workspace design.
- `/static/app.js` provides client-side session, chat, citation, and artifact interactions.

No Node.js build step is required.

## Chat flow

1. The UI creates a conversation through `POST /api/v1/sessions` when the user starts chatting.
2. Messages are sent to `POST /api/v1/chat`.
3. The UI renders the answer as Markdown, shows the provider/model returned by the API, and updates the evidence panel from the returned `sources` and `grounded` fields.
4. Citation buttons such as `[1]` focus the matching source card.
5. Conversation IDs known to the browser are stored in localStorage; opening a conversation reloads its persisted messages from `GET /api/v1/sessions/{session_id}`.

The current API does not expose a list-sessions endpoint. Therefore, the sidebar shows conversations known to this browser, not a global account-level history.

## Artifacts

The Artifacts view can turn an assistant response into an editable Markdown draft. The editor supports Markdown and HTML tabs, a live preview, copying, and file export. Draft content is stored in this browser's localStorage.

HTML preview uses an iframe with an empty sandbox attribute. Scripts, same-origin access, forms, popups, and top-level navigation are not enabled. Do not treat this local draft editor as a persistent server-side artifact store; backend artifact persistence and the dedicated Ship 30 writing skill remain future work.

## Development

Start the API from the repository root:

```powershell
$env:PYTHONPATH = "backend"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the UI or [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the API schema.

The UI expects the same-origin FastAPI API. If serving the frontend separately during development, configure a same-origin proxy or add a narrowly scoped CORS policy before changing the API base URL.
