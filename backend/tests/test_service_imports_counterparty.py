"""Matching fuzzy et création auto-pending de contreparties."""
import pytest
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.services.imports import match_or_create_counterparty


def _make_entity(session: Session) -> Entity:
    e = Entity(name="SAS Test", legal_name="SAS Test SARL")
    session.add(e)
    session.flush()
    return e


def test_match_returns_none_when_hint_empty(db_session: Session) -> None:
    e = _make_entity(db_session)
    cp, created = match_or_create_counterparty(db_session, entity_id=e.id, hint=None)
    assert cp is None
    assert created is False


def test_match_finds_existing_active_fuzzy(db_session: Session) -> None:
    e = _make_entity(db_session)
    existing = Counterparty(
        entity_id=e.id, name="ACME SAS", normalized_name="ACME SAS",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add(existing)
    db_session.flush()
    cp, created = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="ACME S.A.S."
    )
    assert cp is not None
    assert cp.id == existing.id
    assert created is False


def test_match_creates_pending_when_no_existing(db_session: Session) -> None:
    e = _make_entity(db_session)
    cp, created = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="NEW PARTNER SARL"
    )
    assert cp is not None
    assert cp.status == CounterpartyStatus.PENDING
    assert cp.name == "NEW PARTNER SARL"
    assert cp.normalized_name == "NEW PARTNER SARL"
    assert created is True


def test_match_creates_distinct_pending_when_fuzzy_below_threshold(db_session: Session) -> None:
    e = _make_entity(db_session)
    existing = Counterparty(
        entity_id=e.id, name="ACME SAS", normalized_name="ACME SAS",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add(existing)
    db_session.flush()
    cp, created = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="COMPLETELY DIFFERENT GMBH"
    )
    assert cp is not None
    assert cp.id != existing.id
    assert cp.status == CounterpartyStatus.PENDING
    assert created is True


def test_match_returns_existing_pending_not_created_flag(db_session: Session) -> None:
    """Une pending existante matchée par fuzzy ne doit PAS être comptée comme créée."""
    e = _make_entity(db_session)
    existing = Counterparty(
        entity_id=e.id, name="PRIOR PENDING SARL", normalized_name="PRIOR PENDING SARL",
        status=CounterpartyStatus.PENDING,
    )
    db_session.add(existing)
    db_session.flush()
    cp, created = match_or_create_counterparty(
        db_session, entity_id=e.id, hint="PRIOR PENDING SARL"
    )
    assert cp is not None
    assert cp.id == existing.id
    assert created is False
