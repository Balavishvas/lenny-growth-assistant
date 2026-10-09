"""Tests for the database readiness endpoint without requiring a live database."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import main  # noqa: E402

client = TestClient(main.app)


def test_database_health_returns_connected(monkeypatch) -> None:
    monkeypatch.setattr(main, "check_database_connection", lambda: True)

    response = client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_returns_safe_error_when_unavailable(monkeypatch) -> None:
    def fail_connection():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(main, "check_database_connection", fail_connection)

    response = client.get("/health/database")

    assert response.status_code == 503
    assert "Database unavailable" in response.json()["detail"]
    assert "connection refused" not in response.text
