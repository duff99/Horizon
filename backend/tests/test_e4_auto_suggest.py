"""E4 — GET /api/rules/auto-suggest retourne les patterns manuels répétés."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique() -> str:
    return uuid.uuid4().hex


def _create_entity(db_session: Session) -> Entity:
    n = f"Entité E4 {_unique()}"
    e = Entity(name=n, legal_name=n)
    db_session.add(e)
    db_session.flush()
    return e


def _create_bank_account(db_session: Session, entity_id: int) -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76000{_unique()[:20]}",
        name=f"Compte E4 {_unique()}",
    )
    db_session.add(ba)
    db_session.flush()
    return ba


def _create_import(db_session: Session, bank_account_id: int) -> ImportRecord:
    imp = ImportRecord(
        bank_account_id=bank_account_id,
        filename="test.pdf",
        file_sha256=_unique() * 2,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db_session.add(imp)
    db_session.flush()
    return imp


def _create_category(db_session: Session, name: str = "Test Cat") -> Category:
    cat = Category(name=f"{name} {_unique()}", slug=_unique())
    db_session.add(cat)
    db_session.flush()
    return cat


def _create_manual_tx(
    db_session: Session,
    bank_account_id: int,
    import_id: int,
    normalized_label: str,
    category_id: int,
) -> Transaction:
    key = _unique()
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=import_id,
        operation_date=date(2026, 1, 15),
        value_date=date(2026, 1, 15),
        amount=Decimal("-100.00"),
        label=normalized_label,
        raw_label=normalized_label,
        normalized_label=normalized_label,
        dedup_key=key[:64],
        statement_row_index=0,
        categorized_by=TransactionCategorizationSource.MANUAL,
        category_id=category_id,
        categorization_rule_id=None,
    )
    db_session.add(tx)
    db_session.flush()
    return tx


def _login_user(client, db_session: Session, entity_id: int | None = None) -> User:
    u = User(
        email=f"{_unique()}@test.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.ADMIN,
    )
    db_session.add(u)
    db_session.flush()
    if entity_id is not None:
        db_session.add(UserEntityAccess(user_id=u.id, entity_id=entity_id))
        db_session.flush()
    db_session.commit()
    resp = client.post("/api/auth/login", json={"email": u.email, "password": "test-password-123"})
    assert resp.status_code == 200
    return u


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_auto_suggest_returns_pattern(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Test categorie")
    # Utiliser un label unique qui ne correspond à aucune règle existante
    unique_label = f"FOURNISSEUR UNIQUE {_unique()[:8]}"
    # 3 transactions MANUAL avec le même normalized_label -> doit apparaître
    for _ in range(3):
        _create_manual_tx(db_session, ba.id, imp.id, unique_label, cat.id)
    db_session.commit()

    _login_user(client, db_session, entity_id=entity.id)

    resp = client.get("/api/rules/auto-suggest")
    assert resp.status_code == 200
    data = resp.json()
    labels = [s["normalized_label"] for s in data]
    assert unique_label in labels


def test_auto_suggest_requires_min_3(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Test categorie 2")
    # Seulement 2 occurrences — ne doit PAS apparaître
    for _ in range(2):
        _create_manual_tx(db_session, ba.id, imp.id, "PRLV UNIQUEMENT 2X", cat.id)
    db_session.commit()

    _login_user(client, db_session, entity_id=entity.id)

    resp = client.get("/api/rules/auto-suggest")
    assert resp.status_code == 200
    data = resp.json()
    labels = [s["normalized_label"] for s in data]
    assert "PRLV UNIQUEMENT 2X" not in labels


def test_auto_suggest_custom_min_count(client, db_session):
    """min_count=2 doit inclure les patterns avec 2 occurrences."""
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Test min count")
    for _ in range(2):
        _create_manual_tx(db_session, ba.id, imp.id, "PRLV MIN2", cat.id)
    db_session.commit()

    _login_user(client, db_session, entity_id=entity.id)

    resp = client.get("/api/rules/auto-suggest?min_count=2")
    assert resp.status_code == 200
    data = resp.json()
    labels = [s["normalized_label"] for s in data]
    assert "PRLV MIN2" in labels


def test_auto_suggest_excludes_already_covered_by_rule(client, db_session):
    """Un pattern déjà couvert par une règle existante ne doit pas être suggéré."""
    from app.models.categorization_rule import CategorizationRule

    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Test covered")

    # Créer une règle qui couvre le pattern
    rule = CategorizationRule(
        name=f"Règle test {_unique()}",
        priority=9800,
        is_system=False,
        label_operator="CONTAINS",
        label_value="PRLV COUVERT",
        direction="ANY",
        category_id=cat.id,
    )
    db_session.add(rule)
    db_session.flush()

    # 3 transactions manuelles catégorisées SANS règle (categorization_rule_id=None)
    for _ in range(3):
        _create_manual_tx(db_session, ba.id, imp.id, "PRLV COUVERT", cat.id)
    db_session.commit()

    _login_user(client, db_session, entity_id=entity.id)

    resp = client.get("/api/rules/auto-suggest")
    assert resp.status_code == 200
    data = resp.json()
    labels = [s["normalized_label"] for s in data]
    # Ce pattern est déjà couvert par une règle => ne doit pas apparaître
    assert "PRLV COUVERT" not in labels


def test_auto_suggest_response_structure(client, db_session):
    """Vérifie la structure de la réponse."""
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Test struct")
    for _ in range(3):
        _create_manual_tx(db_session, ba.id, imp.id, "PRLV STRUCT", cat.id)
    db_session.commit()

    _login_user(client, db_session, entity_id=entity.id)

    resp = client.get("/api/rules/auto-suggest")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    if items:
        item = next((i for i in items if i["normalized_label"] == "PRLV STRUCT"), None)
        assert item is not None
        assert "normalized_label" in item
        assert "category_id" in item
        assert "category_name" in item
        assert "manual_count" in item
        assert item["manual_count"] >= 3
