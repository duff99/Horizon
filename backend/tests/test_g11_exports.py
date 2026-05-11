"""Tests pour G11 — Export CSV généralisé.

Couvre :
- GET /api/admin/audit-log/export (admin only)
- GET /api/transactions/export (multi-tenant)
- GET /api/analysis/drift/export
- GET /api/analysis/top-movers/export
- GET /api/analysis/mom/export (remplace yoy/export — Plan I2)
- GET /api/forecast/pivot/export
- 400 si format=xlsx demandé (openpyxl absent en test)
- 403 si entité non accessible
"""
from __future__ import annotations

import io
import csv
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.forecast_scenario import ForecastScenario
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv(content: bytes) -> list[list[str]]:
    """Parse un CSV UTF-8 avec BOM."""
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    return list(reader)


def _make_entity_with_access(db: Session, user: User, name: str) -> tuple[Entity, BankAccount]:
    entity = Entity(name=name, legal_name=name)
    db.add(entity)
    db.flush()
    access = UserEntityAccess(user_id=user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76{entity.id:020d}",
        name=f"Compte {name}",
    )
    db.add_all([access, ba])
    db.flush()
    return entity, ba


def _make_transaction(db: Session, ba: BankAccount, amount: Decimal, label: str, row_idx: int) -> Transaction:
    today = date.today()
    ir = ImportRecord(
        bank_account_id=ba.id,
        bank_code=ba.bank_code,
        status=ImportStatus.COMPLETED,
        period_start=today.replace(day=1),
        period_end=today,
        opening_balance=Decimal("0"),
        closing_balance=amount,
        imported_count=1,
    )
    db.add(ir)
    db.flush()
    tx = Transaction(
        bank_account_id=ba.id,
        import_id=ir.id,
        operation_date=today,
        value_date=today,
        amount=amount,
        label=label,
        raw_label=label,
        dedup_key=f"g11-{ba.id}-{row_idx}",
        statement_row_index=row_idx,
        is_aggregation_parent=False,
        normalized_label=label.lower(),
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db.add(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Audit log export
# ---------------------------------------------------------------------------

def test_audit_export_csv_basic(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV du journal d'audit — admin only. Vérifie BOM, séparateur, en-têtes."""
    # Insérer une entrée d'audit
    entry = AuditLog(
        user_id=auth_user.id,
        user_email=auth_user.email,
        action="create",
        entity_type="Entity",
        entity_id="42",
    )
    db_session.add(entry)
    db_session.commit()

    resp = client.get("/api/admin/audit-log/export")
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers["content-type"]
    assert "audit-log_" in resp.headers["content-disposition"]
    assert ".csv" in resp.headers["content-disposition"]

    rows = _parse_csv(resp.content)
    assert len(rows) >= 2  # header + au moins 1 ligne
    assert rows[0][0] == "Date/heure"
    assert rows[0][1] == "Utilisateur"


def test_audit_export_csv_filters(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Le filtre action=create retourne uniquement les lignes create."""
    entry_create = AuditLog(
        user_email="x@x.com", action="create", entity_type="A", entity_id="1",
    )
    entry_delete = AuditLog(
        user_email="x@x.com", action="delete", entity_type="A", entity_id="2",
    )
    db_session.add_all([entry_create, entry_delete])
    db_session.commit()

    resp = client.get("/api/admin/audit-log/export?action=create")
    assert resp.status_code == 200
    rows = _parse_csv(resp.content)
    data_rows = rows[1:]
    assert all(r[2] == "create" for r in data_rows if r)


def test_audit_export_xlsx_unavailable(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """format=xlsx → 400 si openpyxl absent (cas prod actuel)."""
    import app.api._export_helpers as helpers
    original = helpers.XLSX_AVAILABLE
    helpers.XLSX_AVAILABLE = False
    try:
        resp = client.get("/api/admin/audit-log/export?format=xlsx")
        assert resp.status_code == 400
        assert "XLSX" in resp.json()["detail"]
    finally:
        helpers.XLSX_AVAILABLE = original


# ---------------------------------------------------------------------------
# 2. Transactions export
# ---------------------------------------------------------------------------

def test_transactions_export_csv_basic(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV des transactions — structure correcte."""
    entity, ba = _make_entity_with_access(db_session, auth_user, "G11 TxExport")
    _make_transaction(db_session, ba, Decimal("-500.00"), "Loyer bureau", 1)
    db_session.commit()

    resp = client.get(f"/api/transactions/export?entity_id={entity.id}")
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers["content-type"]
    assert "transactions_" in resp.headers["content-disposition"]

    rows = _parse_csv(resp.content)
    assert rows[0] == ["Date", "Libelle", "Tiers", "Categorie", "Montant (EUR)", "Compte"]
    assert len(rows) >= 2


def test_transactions_export_403_foreign_entity(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Entité non accessible au reader → 403."""
    other = Entity(name="G11 Autre", legal_name="G11 Autre")
    db_session.add(other)
    db_session.commit()

    resp = client.get(f"/api/transactions/export?entity_id={other.id}")
    assert resp.status_code == 403


def test_transactions_export_with_date_range(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Regression : un filtre date_from/date_to ne doit pas faire crasher
    l'endpoint en 500 (le paramètre était typé str → comparaison
    date >= VARCHAR refusée par SQLAlchemy).
    """
    entity, ba = _make_entity_with_access(db_session, auth_user, "G11 DateRange")
    _make_transaction(db_session, ba, Decimal("-100.00"), "TxDate", 1)
    db_session.commit()

    today = date.today()
    resp = client.get(
        f"/api/transactions/export?entity_id={entity.id}"
        f"&date_from={today.isoformat()}&date_to={today.isoformat()}"
    )
    assert resp.status_code == 200, resp.text
    rows = _parse_csv(resp.content)
    assert len(rows) >= 2  # header + 1 tx


def test_transactions_export_counterparty_includes_sepa_children(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Regression : symétrique avec GET /api/transactions. Un filtre par
    tier doit faire ressortir ses enfants SEPA même sans toggle SEPA.
    Sans ce fix, le CSV était vide pour les tiers payés en masse SEPA.
    """
    from app.models.counterparty import Counterparty

    entity, ba = _make_entity_with_access(db_session, auth_user, "G11 SepaCp")
    cp = Counterparty(entity_id=entity.id, name="Salarié X", normalized_name="salarie x")
    db_session.add(cp)
    db_session.flush()
    parent = _make_transaction(db_session, ba, Decimal("-3000.00"), "SEPA BATCH", 10)
    db_session.commit()
    child = _make_transaction(db_session, ba, Decimal("-1500.00"), "SEPA child", 11)
    child.parent_transaction_id = parent.id
    child.counterparty_id = cp.id
    db_session.commit()

    resp = client.get(
        f"/api/transactions/export?entity_id={entity.id}&counterparty_id={cp.id}"
    )
    assert resp.status_code == 200, resp.text
    rows = _parse_csv(resp.content)
    # header + au moins une ligne (l'enfant SEPA)
    assert len(rows) >= 2, "L'enfant SEPA du tiers doit apparaître dans l'export"


def test_transactions_export_bom(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Le fichier CSV commence par le BOM UTF-8 (EF BB BF)."""
    entity, ba = _make_entity_with_access(db_session, auth_user, "G11 BOM")
    _make_transaction(db_session, ba, Decimal("1000.00"), "Vente", 99)
    db_session.commit()

    resp = client.get(f"/api/transactions/export?entity_id={entity.id}")
    assert resp.status_code == 200
    # BOM UTF-8 = bytes EF BB BF
    assert resp.content[:3] == b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------
# 3. Analysis — drift export
# ---------------------------------------------------------------------------

def test_drift_export_csv(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV des dérives — en-têtes corrects, statut 200."""
    entity, _ba = _make_entity_with_access(db_session, auth_user, "G11 Drift")
    db_session.commit()

    resp = client.get(f"/api/analysis/drift/export?entity_id={entity.id}")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    rows = _parse_csv(resp.content)
    assert rows[0][0] == "Categorie"


def test_drift_export_403(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Entité non accessible → 403."""
    other = Entity(name="G11 Drift Autre", legal_name="G11 Drift Autre")
    db_session.add(other)
    db_session.commit()

    resp = client.get(f"/api/analysis/drift/export?entity_id={other.id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 4. Analysis — top-movers export
# ---------------------------------------------------------------------------

def test_top_movers_export_csv(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV top movers — statut 200 et en-têtes corrects."""
    entity, _ba = _make_entity_with_access(db_session, auth_user, "G11 TopMovers")
    db_session.commit()

    resp = client.get(f"/api/analysis/top-movers/export?entity_id={entity.id}")
    assert resp.status_code == 200
    rows = _parse_csv(resp.content)
    assert rows[0] == ["Categorie", "Direction", "Variation (EUR)"]


# ---------------------------------------------------------------------------
# 5. Analysis — mom export (remplace yoy export — Plan I2)
# ---------------------------------------------------------------------------

def test_mom_export_csv(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV MoM 6 mois — header + jusqu'à 6 mois."""
    entity, _ba = _make_entity_with_access(db_session, auth_user, "G11 MoM")
    db_session.commit()

    resp = client.get(f"/api/analysis/mom/export?entity_id={entity.id}")
    assert resp.status_code == 200
    rows = _parse_csv(resp.content)
    # header + jusqu'à 6 mois (0 si pas de data, mais header présent)
    assert len(rows) >= 1
    assert rows[0][0] == "Mois"
    assert rows[0][1] == "Encaissements (EUR)"


# ---------------------------------------------------------------------------
# 6. Forecast pivot export
# ---------------------------------------------------------------------------

def test_pivot_export_csv(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV pivot — statut 200 et Content-Disposition correct."""
    entity, _ba = _make_entity_with_access(db_session, auth_user, "G11 Pivot")
    scenario = ForecastScenario(
        entity_id=entity.id,
        name="Scenario G11",
        is_default=True,
    )
    db_session.add(scenario)
    db_session.commit()

    today = date.today()
    from_str = today.strftime("%Y-%m")
    to_str = today.strftime("%Y-%m")

    resp = client.get(
        f"/api/forecast/pivot/export?scenario_id={scenario.id}"
        f"&entity_id={entity.id}&from={from_str}&to={to_str}"
    )
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers["content-type"]
    assert "previsionnel-pivot_" in resp.headers["content-disposition"]


def test_pivot_export_403_wrong_scenario(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Scénario rattaché à une autre entité → 403."""
    entity_a, _ = _make_entity_with_access(db_session, auth_user, "G11 Pivot A")
    entity_b = Entity(name="G11 Pivot B", legal_name="G11 Pivot B")
    db_session.add(entity_b)
    db_session.flush()
    scenario_b = ForecastScenario(
        entity_id=entity_b.id, name="Scenario B", is_default=True
    )
    db_session.add(scenario_b)
    db_session.commit()

    today = date.today()
    from_str = today.strftime("%Y-%m")
    resp = client.get(
        f"/api/forecast/pivot/export?scenario_id={scenario_b.id}"
        f"&entity_id={entity_a.id}&from={from_str}&to={from_str}"
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7. XLSX non disponible — mock
# ---------------------------------------------------------------------------

def test_transactions_export_xlsx_unavailable(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """format=xlsx sur /transactions/export → 400 si openpyxl absent."""
    import app.api._export_helpers as helpers
    original = helpers.XLSX_AVAILABLE
    helpers.XLSX_AVAILABLE = False
    try:
        entity, ba = _make_entity_with_access(db_session, auth_user, "G11 XLSX Tx")
        db_session.commit()
        resp = client.get(f"/api/transactions/export?entity_id={entity.id}&format=xlsx")
        assert resp.status_code == 400
        assert "XLSX" in resp.json()["detail"]
    finally:
        helpers.XLSX_AVAILABLE = original
