"""Smoke tests for the API's initial vertical slice."""

import sys
from pathlib import Path

# Make the backend package importable when pytest is run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def test_health_returns_liveness_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "Lenny Growth Assistant"
