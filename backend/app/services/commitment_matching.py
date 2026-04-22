"""Matching engagements ↔ transactions.

Heuristique de score (voir spec 2026-04-22-plan-5b) :
    score = 100 - abs(amount_diff_eur) - abs(date_diff_days)*2
            + (20 si counterparty matche)

Filtres pour un commitment `pending` :
- entity_id identique (via bank_account.entity_id de la tx)
- direction identique (out ↔ tx négative, in ↔ tx positive)
- tx non déjà matchée par un autre commitment
- operation_date dans [expected_date - 7j, expected_date + 7j]
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.transaction import Transaction

AUTO_MATCH_THRESHOLD = 80
DATE_WINDOW_DAYS = 7


def _direction_of_tx(tx: Transaction) -> CommitmentDirection:
    return (
        CommitmentDirection.OUT
        if tx.amount is not None and tx.amount < Decimal("0")
        else CommitmentDirection.IN
    )


def _score(
    commitment: Commitment, tx: Transaction, *, counterparty_bonus: bool
) -> int:
    # Montant commitment en euros (positif). Montant tx en euros (signé).
    commitment_eur = Decimal(commitment.amount_cents) / Decimal(100)
    tx_abs = abs(tx.amount)
    amount_diff = abs(commitment_eur - tx_abs)
    date_diff = abs((tx.operation_date - commitment.expected_date).days)
    score = 100 - int(amount_diff) - date_diff * 2
    if counterparty_bonus:
        score += 20
    return score


def suggest_matches(
    session: Session,
    commitment: Commitment,
    *,
    limit: int = 10,
) -> list[tuple[Transaction, int]]:
    """Retourne les `limit` meilleures transactions candidates triées par score desc.

    N.B. inclut aussi les transactions déjà liées à *ce* commitment (utile
    pour la reprise UI), mais exclut celles liées à d'autres commitments.
    """
    window_start = commitment.expected_date - timedelta(days=DATE_WINDOW_DAYS)
    window_end = commitment.expected_date + timedelta(days=DATE_WINDOW_DAYS)

    # Bank accounts de l'entité
    bank_accounts = list(
        session.scalars(
            select(BankAccount.id).where(BankAccount.entity_id == commitment.entity_id)
        )
    )
    if not bank_accounts:
        return []

    # Transactions déjà liées à un *autre* commitment (à exclure)
    already_matched = set(
        session.scalars(
            select(Commitment.matched_transaction_id).where(
                and_(
                    Commitment.matched_transaction_id.is_not(None),
                    Commitment.id != commitment.id,
                )
            )
        )
    )

    txs = session.execute(
        select(Transaction).where(
            and_(
                Transaction.bank_account_id.in_(bank_accounts),
                Transaction.operation_date >= window_start,
                Transaction.operation_date <= window_end,
            )
        )
    ).scalars().all()

    scored: list[tuple[Transaction, int]] = []
    for tx in txs:
        if tx.id in already_matched:
            continue
        if _direction_of_tx(tx) != commitment.direction:
            continue
        cp_bonus = (
            commitment.counterparty_id is not None
            and tx.counterparty_id is not None
            and tx.counterparty_id == commitment.counterparty_id
        )
        score = _score(commitment, tx, counterparty_bonus=cp_bonus)
        scored.append((tx, score))

    scored.sort(key=lambda p: p[1], reverse=True)
    return scored[:limit]


def suggest_matches_for_tx(
    session: Session, tx: Transaction,
) -> Optional[Commitment]:
    """Cherche l'unique commitment `pending` à lier à cette transaction.

    Utilisé par le pipeline d'import pour l'auto-matching. Retourne le
    commitment si :
    - exactement 1 commitment candidate a un score >= AUTO_MATCH_THRESHOLD, OU
    - plusieurs candidats mais un seul possède le meilleur score (strict).
    Sinon retourne None (ambigu → action manuelle).
    """
    ba = session.get(BankAccount, tx.bank_account_id)
    if ba is None:
        return None

    direction = _direction_of_tx(tx)

    # Cherche les commitments pending de l'entité, direction identique,
    # dans la fenêtre temporelle inverse.
    candidates = session.execute(
        select(Commitment).where(
            and_(
                Commitment.entity_id == ba.entity_id,
                Commitment.direction == direction,
                Commitment.status == CommitmentStatus.PENDING,
                Commitment.matched_transaction_id.is_(None),
                Commitment.expected_date
                >= tx.operation_date - timedelta(days=DATE_WINDOW_DAYS),
                Commitment.expected_date
                <= tx.operation_date + timedelta(days=DATE_WINDOW_DAYS),
            )
        )
    ).scalars().all()

    if not candidates:
        return None

    scored: list[tuple[Commitment, int]] = []
    for c in candidates:
        cp_bonus = (
            c.counterparty_id is not None
            and tx.counterparty_id is not None
            and tx.counterparty_id == c.counterparty_id
        )
        s = _score(c, tx, counterparty_bonus=cp_bonus)
        if s >= AUTO_MATCH_THRESHOLD:
            scored.append((c, s))

    if not scored:
        return None
    # Prend le meilleur, mais doit être strictement unique
    scored.sort(key=lambda p: p[1], reverse=True)
    if len(scored) >= 2 and scored[0][1] == scored[1][1]:
        return None
    return scored[0][0]
