"""GET /api/admin/audit-log with action=merge filter."""
import pytest
from fastapi.testclient import TestClient


def test_audit_log_filter_merge_action(
    client: TestClient, auth_user,
) -> None:
    """GET /api/admin/audit-log?action=merge returns 200 (not 422)."""
    r = client.get("/api/admin/audit-log?action=merge")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert "total" in body


def test_audit_log_filter_invalid_action(
    client: TestClient, auth_user,
) -> None:
    """GET /api/admin/audit-log?action=delete_all returns 422 (validation error)."""
    r = client.get("/api/admin/audit-log?action=delete_all")
    assert r.status_code == 422, r.text
