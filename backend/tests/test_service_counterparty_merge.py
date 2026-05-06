"""Service de fusion de contreparties — preview et exécution."""
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.services.counterparty_merge import build_merge_preview, execute_merge


def _import(session: Session, ba) -> ImportRecord:
    imp = ImportRecord(
        bank_account_id=ba.id, filename="m.pdf",
        file_sha256="b" * 64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    session.add(imp); session.flush()
    return imp


def _tx(ba, imp, cp_id: int, dedup: str, amount: str = "10") -> Transaction:
    return Transaction(
        bank_account_id=ba.id, import_id=imp.id, counterparty_id=cp_id,
        operation_date=date(2026, 4, 1), value_date=date(2026, 4, 1),
        label="X", raw_label="X", amount=Decimal(amount),
        dedup_key=dedup, statement_row_index=1,
    )


def test_preview_counts_impacted_rows(
    db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    imp = _import(db_session, ba)
    src = Counterparty(
        entity_id=e_id, name="CARREFOUR", normalized_name="CARREFOUR",
        status=CounterpartyStatus.ACTIVE,
    )
    tgt = Counterparty(
        entity_id=e_id, name="Carrefour Proxi", normalized_name="CARREFOUR PROXI",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add_all([src, tgt]); db_session.flush()

    db_session.add(_tx(ba, imp, src.id, "dk1"))
    db_session.add(Commitment(
        entity_id=e_id, counterparty_id=src.id,
        direction=CommitmentDirection.OUT, amount_cents=10000,
        issue_date=date(2026, 4, 1), expected_date=date(2026, 5, 1),
        status=CommitmentStatus.PENDING,
    ))
    db_session.commit()

    preview = build_merge_preview(db_session, source_id=src.id, target_id=tgt.id)
    assert preview.source_id == src.id
    assert preview.target_id == tgt.id
    assert preview.transaction_count == 1
    assert len(preview.commitments) == 1
    assert preview.commitments[0].amount == 100.0


def test_execute_merge_reattaches_and_deletes_source(
    db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    imp = _import(db_session, ba)
    src = Counterparty(
        entity_id=e_id, name="A", normalized_name="A",
        status=CounterpartyStatus.ACTIVE,
    )
    tgt = Counterparty(
        entity_id=e_id, name="B", normalized_name="B",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add_all([src, tgt]); db_session.flush()
    db_session.add(_tx(ba, imp, src.id, "dk1"))
    db_session.commit()

    execute_merge(db_session, source_id=src.id, target_id=tgt.id)
    db_session.commit()

    assert db_session.get(Counterparty, src.id) is None
    tgt_txs = db_session.query(Transaction).filter_by(counterparty_id=tgt.id).count()
    assert tgt_txs == 1


def test_execute_merge_rejects_cross_entity(db_session: Session) -> None:
    e1 = Entity(name="E1", legal_name="E1 SARL")
    e2 = Entity(name="E2", legal_name="E2 SARL")
    db_session.add_all([e1, e2]); db_session.flush()
    src = Counterparty(
        entity_id=e1.id, name="A", normalized_name="A",
        status=CounterpartyStatus.ACTIVE,
    )
    tgt = Counterparty(
        entity_id=e2.id, name="B", normalized_name="B",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add_all([src, tgt]); db_session.commit()
    with pytest.raises(ValueError, match="entity"):
        execute_merge(db_session, source_id=src.id, target_id=tgt.id)


def test_api_merge_preview_endpoint(
    client: TestClient, db_session: Session, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    src = Counterparty(
        entity_id=e_id, name="A", normalized_name="A",
        status=CounterpartyStatus.ACTIVE,
    )
    tgt = Counterparty(
        entity_id=e_id, name="B", normalized_name="B",
        status=CounterpartyStatus.ACTIVE,
    )
    db_session.add_all([src, tgt]); db_session.commit()

    resp = client.get(
        f"/api/counterparties/{src.id}/merge-preview",
        params={"target_id": tgt.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_id"] == src.id
    assert body["target_id"] == tgt.id
