"""GET /api/categories."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_categories_returns_all_seeded(
    client: TestClient,
    auth_user,
) -> None:
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Expect at least 9 root categories + 40 sub-categories seeded by migrations
    assert len(data) >= 49, f"Expected ≥49 categories, got {len(data)}"
    roots = [c for c in data if c["parent_category_id"] is None]
    subs = [c for c in data if c["parent_category_id"] is not None]
    assert len(roots) >= 9, f"Expected ≥9 roots, got {len(roots)}"
    assert len(subs) >= 40, f"Expected ≥40 sub-categories, got {len(subs)}"
    # Verify response shape
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "slug" in first
    assert "parent_category_id" in first


def test_list_categories_requires_auth(
    client: TestClient,
) -> None:
    resp = client.get("/api/categories")
    assert resp.status_code == 401
