"""Test de perf : `compute_pivot` doit batch-loader ses queries.

Plan 5c Phase 1 : le pivot historique faisait ~750 SELECT pour 15 mois × 50
catégories (cascade `_sum_transactions`/`_sum_commitments`/`_sum_forecast_entries`
+ un lookup `ForecastLine` par cell). L'objectif est de réduire ce coût à
quelques requêtes de préchargement via `_preload()`.

Ce test mesure le nombre de SELECT exécutés sur le pivot via le hook SQLAlchemy
``before_cursor_execute``. Tolérance : ≤ 10 (marge sur les ~4 attendues).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.forecast_line import ForecastLine, ForecastLineMethod
from app.models.forecast_scenario import ForecastScenario
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.services.forecast_engine import _add_months, _first_of_month, compute_pivot


@pytest.fixture()
def perf_ctx(db_session: Session) -> dict:
    """Seed : 10 catégories × 5 tx/mois × 12 mois, + 2 forecast lines."""
    entity = Entity(name="EPerf", legal_name="EPerf")
    db_session.add(entity)
    db_session.flush()

    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000777",
        name="ComptePerf",
    )
    db_session.add(ba)
    db_session.flush()

    scenario = ForecastScenario(
        entity_id=entity.id, name="Principal", is_default=True
    )
    db_session.add(scenario)
    db_session.flush()

    # 10 catégories
    categories: list[Category] = []
    for i in range(10):
        cat = Category(name=f"PerfCat{i}", slug=f"perfcat-{i}")
        db_session.add(cat)
        categories.append(cat)
    db_session.flush()

    ir = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        filename="perf.pdf",
        status=ImportStatus.COMPLETED,
        imported_count=0,
    )
    db_session.add(ir)
    db_session.flush()

    current_first = _first_of_month(date.today())
    # 12 mois d'historique (M-12 … M-1) × 10 catégories × 5 tx/mois
    row_index = 0
    for month_offset in range(1, 13):
        m = _add_months(current_first, -month_offset)
        op_date = date(m.year, m.month, 15)
        for cat_idx, cat in enumerate(categories):
            base_amount = Decimal("100.00") * (cat_idx + 1)
            for n in range(5):
                row_index += 1
                db_session.add(
                    Transaction(
                        bank_account_id=ba.id,
                        import_id=ir.id,
                        operation_date=op_date,
                        value_date=op_date,
                        amount=base_amount,
                        label=f"Perf {cat.slug} {month_offset} {n}",
                        raw_label=f"Perf {cat.slug} {month_offset} {n}",
                        dedup_key=f"perf-{cat.slug}-{month_offset}-{n}",
                        statement_row_index=row_index,
                        category_id=cat.id,
                        normalized_label=f"perf {cat.slug} {month_offset} {n}",
                    )
                )

    # 2 forecast lines (AVG_3M + FORMULA)
    line_avg = ForecastLine(
        scenario_id=scenario.id,
        entity_id=entity.id,
        category_id=categories[0].id,
        method=ForecastLineMethod.AVG_3M,
    )
    line_formula = ForecastLine(
        scenario_id=scenario.id,
        entity_id=entity.id,
        category_id=categories[1].id,
        method=ForecastLineMethod.FORMULA,
        formula_expr="{PerfCat0} * 2",
    )
    db_session.add_all([line_avg, line_formula])
    db_session.commit()
    db_session.refresh(entity)
    db_session.refresh(scenario)
    return {
        "entity": entity,
        "scenario": scenario,
        "current_month": current_first,
    }


def test_compute_pivot_uses_at_most_10_queries(
    db_session: Session, perf_ctx: dict
) -> None:
    """Objectif : ≤ 10 SELECTs pour un pivot 15 mois × 10 catégories."""
    engine = db_session.get_bind()
    query_count = {"n": 0}

    def _before(conn, cursor, statement, params, context, executemany):
        # Ignorer savepoints et commandes transactionnelles
        if statement.strip().upper().startswith("SELECT"):
            query_count["n"] += 1

    event.listen(engine, "before_cursor_execute", _before)
    try:
        current_month = perf_ctx["current_month"]
        result = compute_pivot(
            db_session,
            scenario_id=perf_ctx["scenario"].id,
            entity_id=perf_ctx["entity"].id,
            from_month=_add_months(current_month, -12),
            to_month=_add_months(current_month, 2),
            account_ids=None,
        )
    finally:
        event.remove(engine, "before_cursor_execute", _before)

    # Sanity : le pivot doit produire des lignes
    assert len(result.rows) >= 10
    # Trace utile si la perf régresse
    print(f"[perf] compute_pivot SELECTs = {query_count['n']}")
    assert query_count["n"] <= 10, (
        f"expected <= 10 queries for batched compute_pivot, "
        f"got {query_count['n']}"
    )
