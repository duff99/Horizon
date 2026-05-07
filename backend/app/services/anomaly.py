"""Service de détection des anomalies p95 par catégorie (G4).

Pour chaque catégorie, calcule le p95 du montant absolu des transactions
sur `days` jours. Les transactions des 30 derniers jours dépassant ce p95
sont retournées comme anomalies.

Règles :
- Si une catégorie a moins de MIN_TX_FOR_P95 transactions sur la fenêtre
  analysée, elle est ignorée (p95 non fiable).
- Les transactions is_aggregation_parent=True sont exclues.
- Résultat trié par ratio décroissant, limité à MAX_ANOMALIES.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.anomaly import AnomalyResponse, AnomalyRow

# Nombre minimal de transactions pour calculer un p95 fiable
MIN_TX_FOR_P95 = 5
# Fenêtre de détection des anomalies (transactions récentes)
RECENT_DAYS = 30
# Nombre maximum d'anomalies retournées
MAX_ANOMALIES = 50


def _bank_account_ids_for_entity(session: Session, entity_id: int) -> list[int]:
    return list(
        session.scalars(
            select(BankAccount.id).where(BankAccount.entity_id == entity_id)
        )
    )


def detect_anomalies(
    session: Session,
    *,
    entity_id: int,
    days: int = 180,
) -> AnomalyResponse:
    """Détecte les transactions anormales (montant > p95 historique de la catégorie).

    1. Calcule le p95 du montant absolu par catégorie sur `days` jours.
    2. Retourne les transactions des 30 derniers jours dépassant ce p95.
    """
    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return AnomalyResponse(
            entity_id=entity_id,
            days_analyzed=days,
            anomaly_count=0,
            rows=[],
        )

    today = date.today()
    window_start = today - timedelta(days=days)
    recent_start = today - timedelta(days=RECENT_DAYS)

    # Étape 1 : calculer p95 par catégorie sur toute la fenêtre d'analyse
    # en utilisant func.percentile_cont (PostgreSQL ordered-set aggregate)
    p95_query = (
        select(
            Transaction.category_id,
            func.count(Transaction.id).label("tx_count"),
            func.percentile_cont(0.95)
            .within_group(func.abs(Transaction.amount))
            .label("p95"),
        )
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= window_start,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.is_not(None),
            )
        )
        .group_by(Transaction.category_id)
    )

    p95_by_cat: dict[int, Decimal] = {}
    for row in session.execute(p95_query):
        cat_id, tx_count, p95_val = row
        if cat_id is None or tx_count < MIN_TX_FOR_P95:
            continue
        if p95_val is None or p95_val == 0:
            continue
        p95_by_cat[int(cat_id)] = Decimal(str(p95_val))

    if not p95_by_cat:
        return AnomalyResponse(
            entity_id=entity_id,
            days_analyzed=days,
            anomaly_count=0,
            rows=[],
        )

    # Étape 2 : trouver les transactions récentes qui dépassent le p95
    recent_tx_query = (
        select(
            Transaction.id,
            Transaction.operation_date,
            Transaction.label,
            Transaction.amount,
            Transaction.category_id,
            Category.name.label("category_name"),
        )
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= recent_start,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.in_(list(p95_by_cat.keys())),
            )
        )
    )

    anomalies: list[AnomalyRow] = []
    for tx_id, op_date, label, amount, cat_id, cat_name in session.execute(
        recent_tx_query
    ):
        if cat_id is None:
            continue
        p95 = p95_by_cat.get(int(cat_id))
        if p95 is None:
            continue
        abs_amount = abs(Decimal(str(amount)))
        if abs_amount <= p95:
            continue
        ratio = float(abs_amount / p95)
        p95_cents = int((p95 * Decimal(100)).to_integral_value())
        amount_cents = int((Decimal(str(amount)) * Decimal(100)).to_integral_value())
        anomalies.append(
            AnomalyRow(
                transaction_id=int(tx_id),
                operation_date=op_date,
                label=str(label),
                amount_cents=amount_cents,
                category_id=int(cat_id),
                category_label=str(cat_name) if cat_name else None,
                p95_cents=p95_cents,
                ratio=round(ratio, 2),
            )
        )

    # Tri par ratio décroissant
    anomalies.sort(key=lambda r: -r.ratio)
    anomalies = anomalies[:MAX_ANOMALIES]

    return AnomalyResponse(
        entity_id=entity_id,
        days_analyzed=days,
        anomaly_count=len(anomalies),
        rows=anomalies,
    )
