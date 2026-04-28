"""POST /api/rules/from-transactions."""
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user_entity_access import UserEntityAccess


def _grant_access(db_session, auth_user, bank_account) -> None:
    """auth_user gains access to bank_account.entity_id."""
    db_session.add(
        UserEntityAccess(user_id=auth_user.id, entity_id=bank_account.entity_id)
    )
    db_session.commit()


def test_suggest_rule_from_common_substring(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    _grant_access(db_session, auth_user, bank_account)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="s.pdf",
        file_sha256="s"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    t1 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-50"), label="PRLV URSSAF REF 111",
        raw_label="PRLV URSSAF REF 111",
        normalized_label="PRLV URSSAF REF 111",
        dedup_key="sg-1-" + "s"*58, statement_row_index=0,
    )
    t2 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-50"), label="PRLV URSSAF REF 222",
        raw_label="PRLV URSSAF REF 222",
        normalized_label="PRLV URSSAF REF 222",
        dedup_key="sg-2-" + "s"*58, statement_row_index=1,
    )
    db_session.add_all([t1, t2]); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [t1.id, t2.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "URSSAF" in body["suggested_label_value"]
    assert body["transaction_count"] == 2


@pytest.mark.skip(
    reason="Option C (2026-04) : admin a accès implicite à toutes les entités. "
    "L'IDOR guard testée ici ne s'applique qu'aux readers ; le test devrait être "
    "réécrit avec auth_user_reader + _require_editor désactivé pour le scope rules."
)
def test_suggest_refuses_foreign_transactions(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    """IDOR guard: tx ids on inaccessible entity must yield 404."""
    _grant_access(db_session, auth_user, bank_account)
    # Foreign entity + bank account, no access for auth_user.
    foreign = Entity(name="SAS Foreign", legal_name="SAS Foreign")
    db_session.add(foreign); db_session.flush()
    foreign_ba = BankAccount(
        entity_id=foreign.id, bank_code="delubac", bank_name="Delubac",
        iban="FR7600000000000000000000444",
        name="Compte étranger",
    )
    db_session.add(foreign_ba); db_session.commit()
    imp_f = ImportRecord(
        bank_account_id=foreign_ba.id, filename="f.pdf",
        file_sha256="f"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp_f); db_session.commit()
    foreign_tx = Transaction(
        bank_account_id=foreign_ba.id, import_id=imp_f.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-10"), label="PRLV X",
        raw_label="PRLV X", normalized_label="PRLV X",
        dedup_key="fg-1-" + "f"*58, statement_row_index=0,
    )
    db_session.add(foreign_tx); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [foreign_tx.id],
    })
    assert r.status_code == 404, r.text


def test_suggest_mixed_signs_direction_any(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    """1 debit + 1 credit on same account → direction == 'ANY'."""
    _grant_access(db_session, auth_user, bank_account)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="m.pdf",
        file_sha256="m"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    t_debit = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-50"), label="LOREM 111",
        raw_label="LOREM 111", normalized_label="LOREM 111",
        dedup_key="md-1-" + "m"*58, statement_row_index=0,
    )
    t_credit = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("75"), label="LOREM 222",
        raw_label="LOREM 222", normalized_label="LOREM 222",
        dedup_key="mc-1-" + "m"*58, statement_row_index=1,
    )
    db_session.add_all([t_debit, t_credit]); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [t_debit.id, t_credit.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suggested_direction"] == "ANY"


def test_suggest_falls_back_on_empty_prefix(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    """Two tx with no common prefix → CONTAINS fallback, no crash."""
    _grant_access(db_session, auth_user, bank_account)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="p.pdf",
        file_sha256="p"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    t1 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-10"), label="ABCXYZ",
        raw_label="ABCXYZ", normalized_label="ABCXYZ",
        dedup_key="px-1-" + "p"*58, statement_row_index=0,
    )
    t2 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-20"), label="DEFUVW",
        raw_label="DEFUVW", normalized_label="DEFUVW",
        dedup_key="px-2-" + "p"*58, statement_row_index=1,
    )
    db_session.add_all([t1, t2]); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [t1.id, t2.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "suggested_label_operator" in body
    assert body["suggested_label_operator"] == "CONTAINS"


def test_suggest_handles_empty_labels(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    """Empty normalized_label must not raise IndexError (regression)."""
    _grant_access(db_session, auth_user, bank_account)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="e.pdf",
        file_sha256="e"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    t1 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-10"), label="x",
        raw_label="x", normalized_label="",
        dedup_key="ex-1-" + "e"*58, statement_row_index=0,
    )
    t2 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-20"), label="y",
        raw_label="y", normalized_label="",
        dedup_key="ex-2-" + "e"*58, statement_row_index=1,
    )
    db_session.add_all([t1, t2]); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [t1.id, t2.id],
    })
    assert r.status_code == 200, r.text
