"""Tests C7 — endpoints de santé sous /api et alias racine legacy.

Vérifie que :
- GET /api/healthz → 200 {"status": "alive"}
- GET /api/readyz  → 200 {"status": "ready"}
- GET /healthz     → 200 (alias legacy preservé pour nginx / sondes existantes)
"""

from fastapi.testclient import TestClient


def test_api_healthz(client: TestClient) -> None:
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_api_readyz(client: TestClient) -> None:
    resp = client.get("/api/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_legacy_healthz(client: TestClient) -> None:
    """L'alias /healthz à la racine doit rester disponible (sondes existantes)."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
