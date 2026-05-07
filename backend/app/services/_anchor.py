"""Helper d'ancrage temporel pour les widgets analytiques.

Quand l'utilisateur importe ses relevés en fin de mois, le mois courant est
vide jusqu'à l'import. Les widgets ancrés sur `date.today()` calculent alors
sur des fenêtres qui incluent un mois sans data. `data_anchor` borne `today`
au-dessous par MAX(operation_date) de l'entité.

Sémantique : `data_anchor` est un proxy de "aujourd'hui" qui ne dépasse jamais
la date de la dernière transaction connue. C'est un repère lisible et stable
entre 2 imports.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.transaction import Transaction


def data_anchor(session: Session, entity_id: int | None = None) -> date:
    """Retourne min(today, MAX(operation_date)).

    Si entity_id donné : MAX limité aux comptes de l'entité.
    Si entity_id est None : MAX global sur toutes les transactions non agrégées.
    Si pas de transaction : fallback sur today.
    """
    today = date.today()
    q = select(func.max(Transaction.operation_date)).where(
        Transaction.is_aggregation_parent.is_(False)
    )
    if entity_id is not None:
        q = q.join(BankAccount, BankAccount.id == Transaction.bank_account_id).where(
            BankAccount.entity_id == entity_id
        )
    max_op = session.execute(q).scalar()
    if max_op is None:
        return today
    # max_op peut être un datetime si date_trunc est utilisé ailleurs ;
    # on normalise en date.
    if hasattr(max_op, "date"):
        max_op = max_op.date()
    return min(today, max_op)
