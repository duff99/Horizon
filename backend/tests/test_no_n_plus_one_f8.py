"""F8 — Vérifie l'absence de requêtes N+1 sur les listings critiques.

Méthode : SQLAlchemy event listener + comptage des SELECT émis pendant
le traitement de la requête HTTP.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.entity import Entity
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import hash_password


@pytest.fixture()
def admin_user_f8(db_session: Session) -> User:
    user = User(
        email="admin_f8@example.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        full_name="Admin F8",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_client_f8(client: TestClient, admin_user_f8: User) -> TestClient:
    resp = client.post("/api/auth/login", json={
        "email": admin_user_f8.email,
        "password": "AdminPass123!",
    })
    assert resp.status_code == 200
    return client


@pytest.fixture()
def entity_f8(db_session: Session, admin_user_f8: User) -> Entity:
    e = Entity(name="Entité F8", legal_name="Entité F8")
    db_session.add(e)
    db_session.flush()
    access = UserEntityAccess(user_id=admin_user_f8.id, entity_id=e.id)
    db_session.add(access)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture()
def bank_account_f8(db_session: Session, entity_f8: Entity) -> BankAccount:
    ba = BankAccount(
        entity_id=entity_f8.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000F88",
        name="Compte F8",
    )
    db_session.add(ba)
    db_session.commit()
    db_session.refresh(ba)
    return ba


def _create_commitments(
    db_session: Session,
    entity: Entity,
    bank_account: BankAccount,
    n: int = 10,
) -> None:
    """Crée N engagements de test."""
    for i in range(n):
        c = Commitment(
            entity_id=entity.id,
            bank_account_id=bank_account.id,
            direction=CommitmentDirection.OUT,
            amount_cents=10000 + i * 100,
            issue_date=date(2026, 1, 1),
            expected_date=date(2026, 2, 1),
        )
        db_session.add(c)
    db_session.flush()


def test_list_commitments_no_n_plus_one(
    admin_client_f8: TestClient,
    db_session: Session,
    entity_f8: Entity,
    bank_account_f8: BankAccount,
) -> None:
    """GET /api/commitments avec 10 engagements → nombre de requêtes SQL fixe.

    Avec lazy="joined" sur Commitment.counterparty et Commitment.category,
    toutes les relations sont résolues en un seul JOIN. On autorise un maximum
    de 8 SELECT (très généreux) pour le listing de 10 items.
    Si on avait un N+1 pur, ce serait au minimum 10*2+2 = 22 SELECT.
    """
    _create_commitments(db_session, entity_f8, bank_account_f8, 10)
    db_session.commit()

    queries: list[str] = []
    engine = db_session.bind

    def on_before_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: PLR0913
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", on_before_execute)
    try:
        resp = admin_client_f8.get(f"/api/commitments?entity_id={entity_f8.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10

        select_queries = [
            q for q in queries if q.strip().upper().startswith("SELECT")
        ]
        # Avec lazy="joined", on s'attend à peu de requêtes.
        # On autorise 8 SELECT max (auth session + count + listing + quelques checks).
        # Si N+1 : 10 * 2 + plusieurs = bien plus de 8.
        assert len(select_queries) <= 8, (
            f"Trop de requêtes SQL : {len(select_queries)} SELECT pour 10 engagements. "
            f"Possible N+1 détecté. Requêtes : {select_queries[:5]}"
        )
    finally:
        event.remove(engine, "before_cursor_execute", on_before_execute)


def test_list_rules_no_n_plus_one(
    admin_client_f8: TestClient,
    db_session: Session,
) -> None:
    """GET /api/rules → pas de N+1.

    Les rules n'exposent que des IDs (pas de relation eager chargée).
    On vérifie que le nombre de SELECT reste borné indépendamment du nombre
    de règles existantes.
    """
    queries: list[str] = []
    engine = db_session.bind

    def on_before_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: PLR0913
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", on_before_execute)
    try:
        resp = admin_client_f8.get("/api/rules")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        select_queries = [
            q for q in queries if q.strip().upper().startswith("SELECT")
        ]
        # Rules : pas de relationship eager, serialisation ID-only.
        # On autorise 5 SELECT (auth session + listing + quelques checks).
        assert len(select_queries) <= 5, (
            f"Trop de requêtes SQL : {len(select_queries)} SELECT pour GET /api/rules. "
            "Possible N+1 détecté."
        )
    finally:
        event.remove(engine, "before_cursor_execute", on_before_execute)
