"""GET /api/categories?entity_id=... — accepté mais ignoré (catégories globales)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_categories_accepts_entity_id_noop(
    client: TestClient, auth_user_admin: User,
) -> None:
    # Référence : liste sans param
    resp_ref = client.get("/api/categories")
    assert resp_ref.status_code == 200
    ref_items = resp_ref.json()

    # Avec entity_id arbitraire : même résultat
    resp = client.get("/api/categories", params={"entity_id": 1})
    assert resp.status_code == 200
    assert resp.json() == ref_items
