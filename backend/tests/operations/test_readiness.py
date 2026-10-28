"""Tests for operational health and readiness probes (D06)."""
import shutil
from collections import namedtuple

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])


def test_health_live_endpoint():
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "env" in data


def test_health_ready_endpoint():
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "disk_free_bytes" in data
    assert data["disk_free_bytes"] > 0


def test_health_ready_fails_when_disk_exhausted(monkeypatch):
    # Simulate disk having only 1 KB free (< 10 MB required)
    exhausted = DiskUsage(total=1000000000, used=999999000, free=1024)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: exhausted)

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["code"] == "DISK_SPACE_EXHAUSTED"
    assert "Insufficient free disk space" in data["message"]


def test_health_ready_fails_when_db_down(monkeypatch):
    def fake_execute(self, stmt, *args, **kwargs):
        raise RuntimeError("SQLite database connection lost or file locked")

    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "execute", fake_execute)

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["code"] == "SERVICE_UNAVAILABLE"
    assert "Database connection lost" in data["message"] or "failed" in data["message"]
