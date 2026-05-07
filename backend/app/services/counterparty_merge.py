"""Fusion de contreparties : preview + exécution atomique.

Réattache toutes les FK pointant vers la source (transactions, engagements,
règles de catégorisation, lignes prévisionnelles) vers la cible, puis
supprime la source. La cohérence atomique est de la responsabilité du
caller (ouvrir/commit la transaction).
"""
from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.commitment import Commitment
from app.models.counterparty import Counterparty
from app.models.transaction import Transaction
from app.schemas.counterparty import (
    CounterpartyMergePreview,
    MergeImpactCommitment,
    MergeImpactRule,
)


def _get_pair(
    session: Session, source_id: int, target_id: int,
) -> tuple[Counterparty, Counterparty]:
    src = session.get(Counterparty, source_id)
    tgt = session.get(Counterparty, target_id)
    if src is None or tgt is None:
        raise ValueError("source ou cible introuvable")
    if src.entity_id != tgt.entity_id:
        raise ValueError("fusion impossible entre entity différentes")
    if src.id == tgt.id:
        raise ValueError("source et cible identiques")
    return src, tgt


def build_merge_preview(
    session: Session, *, source_id: int, target_id: int,
) -> CounterpartyMergePreview:
    src, tgt = _get_pair(session, source_id, target_id)

    tx_count = session.query(Transaction).filter_by(counterparty_id=src.id).count()

    rules = (
        session.query(CategorizationRule)
        .filter_by(counterparty_id=src.id)
        .all()
    )
    commitments = (
        session.query(Commitment).filter_by(counterparty_id=src.id).all()
    )

    return CounterpartyMergePreview(
        source_id=src.id, source_name=src.name,
        target_id=tgt.id, target_name=tgt.name,
        transaction_count=tx_count,
        rules=[
            MergeImpactRule(
                id=r.id,
                label=r.label_value,
                category_id=r.category_id,
            )
            for r in rules
        ],
        commitments=[
            MergeImpactCommitment(
                id=c.id,
                direction=c.direction.value,
                amount=c.amount_cents / 100.0,
                expected_date=c.expected_date.isoformat(),
            )
            for c in commitments
        ],
    )


def execute_merge(
    session: Session, *, source_id: int, target_id: int,
) -> None:
    """Réattache toutes les FK source → target puis supprime source.

    À appeler dans une transaction unique côté caller (le commit final
    fait foi). En cas d'erreur, le caller doit rollback.
    """
    src, tgt = _get_pair(session, source_id, target_id)

    session.execute(
        update(Transaction)
        .where(Transaction.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.execute(
        update(Commitment)
        .where(Commitment.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.execute(
        update(CategorizationRule)
        .where(CategorizationRule.counterparty_id == src.id)
        .values(counterparty_id=tgt.id)
    )
    session.delete(src)
    session.flush()
