"""Tests unitaires du service d'audit."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.entity import Entity
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.audit import (
    _to_json_safe,
    audit_context,
    compute_diff,
    record_audit,
    to_dict_for_audit,
)


def _make_user(db: Session, email: str = "actor@example.com") -> User:
    u = User(
        email=email,
        password_hash=hash_password("test-password-123"),
        role=UserRole.ADMIN,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_to_json_safe_handles_primitives() -> None:
    assert _to_json_safe(None) is None
    assert _to_json_safe(42) == 42
    assert _to_json_safe("hello") == "hello"
    assert _to_json_safe(True) is True
    assert _to_json_safe(Decimal("3.14")) == "3.14"
    dt = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    assert _to_json_safe(dt) == dt.isoformat()


def test_to_dict_for_audit_masks_password_hash(db_session: Session) -> None:
    user = _make_user(db_session)
    d = to_dict_for_audit(user)
    assert d["email"] == user.email
    assert d["password_hash"] == "<redacted>"
    assert d["role"] == "admin"


def test_to_dict_for_audit_serializes_enums_and_dates(db_session: Session) -> None:
    user = _make_user(db_session, email="enum@example.com")
    d = to_dict_for_audit(user)
    assert d["role"] == "admin"
    # datetime -> isoformat string
    assert isinstance(d["created_at"], str)
    assert "T" in d["created_at"]


def test_compute_diff_returns_only_changed_fields() -> None:
    before = {"name": "SAS A", "legal_name": "SAS A", "active": True}
    after = {"name": "SAS B", "legal_name": "SAS A", "active": True}
    diff = compute_diff(before, after)
    assert diff == {"name": {"before": "SAS A", "after": "SAS B"}}


def test_compute_diff_empty_when_no_change() -> None:
    same = {"a": 1, "b": 2}
    assert compute_diff(same, same) == {}


def test_compute_diff_empty_when_create_or_delete() -> None:
    assert compute_diff(None, {"a": 1}) == {}
    assert compute_diff({"a": 1}, None) == {}


def test_record_audit_inserts_row(db_session: Session) -> None:
    user = _make_user(db_session)
    e = Entity(name="Test Audit Co", legal_name="Test Audit Co")
    db_session.add(e)
    db_session.flush()

    record_audit(
        db_session,
        user=user,
        action="create",
        entity=e,
        before=None,
        after=to_dict_for_audit(e),
        request=None,
    )
    db_session.commit()

    rows = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "Entity")
        )
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "create"
    assert row.entity_id == str(e.id)
    assert row.user_id == user.id
    assert row.user_email == user.email
    assert row.before_json is None
    assert row.after_json is not None
    assert row.after_json["name"] == "Test Audit Co"


def test_record_audit_computes_diff(db_session: Session) -> None:
    user = _make_user(db_session)
    e = Entity(name="Old Name", legal_name="Old Legal")
    db_session.add(e)
    db_session.flush()

    before = to_dict_for_audit(e)
    e.name = "New Name"
    db_session.flush()
    after = to_dict_for_audit(e)

    record_audit(
        db_session,
        user=user,
        action="update",
        entity=e,
        before=before,
        after=after,
        request=None,
    )
    db_session.commit()

    row = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == "Entity", AuditLog.action == "update")
    ).first()
    assert row is not None
    # Le diff DOIT contenir name changé (autres champs comme updated_at
    # peuvent bouger naturellement, on ne les vérifie pas).
    assert row.diff_json is not None
    assert "name" in row.diff_json
    assert row.diff_json["name"] == {"before": "Old Name", "after": "New Name"}


def test_record_audit_swallows_errors(db_session: Session) -> None:
    """Si l'insert audit échoue, l'exception ne doit PAS se propager."""
    user = _make_user(db_session)
    e = Entity(name="X", legal_name="X")
    db_session.add(e)
    db_session.flush()

    # Passer un before non-sérialisable pour forcer une erreur dans JSONB
    class Unserializable:
        pass

    # Notre _to_json_safe stringify tout, donc on force via un action invalide
    # (bypass CheckConstraint côté DB).
    record_audit(
        db_session,
        user=user,
        action="INVALID_ACTION",  # type: ignore[arg-type] — viole le CHECK
        entity=e,
        before=None,
        after=None,
        request=None,
    )
    # Ne doit pas avoir levé. Un rollback peut être nécessaire pour continuer.
    db_session.rollback()


def test_audit_context_captures_before_and_after(db_session: Session) -> None:
    user = _make_user(db_session)
    e = Entity(name="Ctx Name", legal_name="Ctx Legal")
    db_session.add(e)
    db_session.flush()

    with audit_context(
        db_session, user=user, action="update", entity=e, request=None,
    ):
        e.name = "Ctx New Name"

    db_session.commit()

    row = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity_type == "Entity", AuditLog.action == "update"
        )
    ).first()
    assert row is not None
    assert row.diff_json is not None
    assert row.diff_json["name"] == {
        "before": "Ctx Name", "after": "Ctx New Name"
    }


def test_password_hash_never_leaked_in_audit(db_session: Session) -> None:
    """Sanity : jamais de password_hash en clair dans audit_log."""
    user = _make_user(db_session)
    before = to_dict_for_audit(user)
    user.full_name = "Nouveau nom"
    db_session.flush()
    after = to_dict_for_audit(user)

    record_audit(
        db_session, user=user, action="update", entity=user,
        before=before, after=after, request=None,
    )
    db_session.commit()

    row = db_session.scalars(
        select(AuditLog).where(AuditLog.entity_type == "User")
    ).first()
    assert row is not None
    # before/after/diff : aucun hash lisible
    for blob in (row.before_json, row.after_json, row.diff_json):
        if blob is None:
            continue
        serialized = str(blob)
        assert "password_hash" not in serialized or "<redacted>" in serialized
        # Le vrai hash bcrypt commence par $2b$ — doit être absent.
        assert "$2b$" not in serialized
