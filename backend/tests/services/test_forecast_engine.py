"""Tests du moteur de calcul prévisionnel (Plan 5b Phase 4.2 + 4.3 + 4.4)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.entity import Entity
from app.models.forecast_line import ForecastLine, ForecastLineMethod
from app.models.forecast_scenario import ForecastScenario
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.services.formula_parser import FormulaError
from app.services.forecast_engine import (
    _add_months,
    _first_of_month,
    compute_cell,
    compute_pivot,
)


# ---------------------------------------------------------------------------
# Fixture : entité + comptes + 12 mois d'historique
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine_ctx(db_session: Session) -> dict:
    """Crée un contexte de 12 mois de transactions :
    - Salaires : -3000€/mois
    - Ventes   : +5000€/mois
    sur l'entité + scenario par défaut.
    """
    e = Entity(name="EEngine", legal_name="EEngine")
    db_session.add(e)
    db_session.flush()
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000555",
        name="CompteEngine",
    )
    db_session.add(ba)
    db_session.flush()

    sc = ForecastScenario(entity_id=e.id, name="Principal", is_default=True)
    db_session.add(sc)
    db_session.flush()

    salaires = Category(name="Salaires", slug="salaires-engine")
    ventes = Category(name="Ventes", slug="ventes-engine")
    db_session.add_all([salaires, ventes])
    db_session.flush()

    # Créer un ImportRecord pour satisfaire la FK
    ir = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        filename="fixture.pdf",
        status=ImportStatus.COMPLETED,
        imported_count=0,
    )
    db_session.add(ir)
    db_session.flush()

    current_first = _first_of_month(date.today())
    # 12 mois d'historique : M-12 à M-1
    for i in range(1, 13):
        m = _add_months(current_first, -i)
        # Une tx Salaires (-3000) et une Ventes (+5000) au 15 du mois
        op_date = date(m.year, m.month, 15)
        db_session.add(
            Transaction(
                bank_account_id=ba.id,
                import_id=ir.id,
                operation_date=op_date,
                value_date=op_date,
                amount=Decimal("-3000.00"),
                label=f"Salaire {m}",
                raw_label=f"Salaire {m}",
                dedup_key=f"salaire-{op_date.isoformat()}",
                statement_row_index=i * 2,
                category_id=salaires.id,
                normalized_label=f"salaire {m}",
            )
        )
        db_session.add(
            Transaction(
                bank_account_id=ba.id,
                import_id=ir.id,
                operation_date=op_date,
                value_date=op_date,
                amount=Decimal("5000.00"),
                label=f"Vente {m}",
                raw_label=f"Vente {m}",
                dedup_key=f"vente-{op_date.isoformat()}",
                statement_row_index=i * 2 + 1,
                category_id=ventes.id,
                normalized_label=f"vente {m}",
            )
        )
    db_session.commit()
    db_session.refresh(e)
    db_session.refresh(sc)
    return {
        "entity": e,
        "bank_account": ba,
        "scenario": sc,
        "salaires": salaires,
        "ventes": ventes,
        "current_month": current_first,
    }


# ---------------------------------------------------------------------------
# Méthodes de calcul
# ---------------------------------------------------------------------------


class TestMethods:
    def test_recurring_fixed(self, db_session: Session, engine_ctx: dict) -> None:
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["salaires"].id,
            method=ForecastLineMethod.RECURRING_FIXED,
            amount_cents=-250_000,
        )
        db_session.add(line)
        db_session.commit()
        future_month = _add_months(engine_ctx["current_month"], 1)
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["salaires"].id,
            month=future_month,
        )
        assert cell.forecast_cents == -250_000
        assert cell.realized_cents == 0
        assert cell.total_cents == -250_000

    def test_avg_3m_salaires(self, db_session: Session, engine_ctx: dict) -> None:
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["salaires"].id,
            method=ForecastLineMethod.AVG_3M,
        )
        db_session.add(line)
        db_session.commit()
        # Cible current_month → 3 mois précédents = M-1, M-2, M-3 (tous à -3000€)
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["salaires"].id,
            month=engine_ctx["current_month"],
        )
        # Moyenne sur les 3 mois précédents = -300_000 centimes
        assert cell.forecast_cents == -300_000

    def test_avg_12m_ventes(self, db_session: Session, engine_ctx: dict) -> None:
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["ventes"].id,
            method=ForecastLineMethod.AVG_12M,
        )
        db_session.add(line)
        db_session.commit()
        # Cible current_month → 12 mois précédents M-1..M-12 (tous à +5000€)
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["ventes"].id,
            month=engine_ctx["current_month"],
        )
        assert cell.forecast_cents == 500_000

    def test_previous_month(self, db_session: Session, engine_ctx: dict) -> None:
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["ventes"].id,
            method=ForecastLineMethod.PREVIOUS_MONTH,
        )
        db_session.add(line)
        db_session.commit()
        # Cible = current_month → PREVIOUS_MONTH = M-1 qui a +5000€
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["ventes"].id,
            month=engine_ctx["current_month"],
        )
        assert cell.forecast_cents == 500_000

    def test_same_month_last_year(
        self, db_session: Session, engine_ctx: dict
    ) -> None:
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["ventes"].id,
            method=ForecastLineMethod.SAME_MONTH_LAST_YEAR,
        )
        db_session.add(line)
        db_session.commit()
        # Pour que SAME_MONTH_LAST_YEAR renvoie les ventes d'il y a 12 mois,
        # il faut interroger sur current_month. current - 12 → M-12 qui a une vente +5000€
        current = engine_ctx["current_month"]
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["ventes"].id,
            month=current,
        )
        assert cell.forecast_cents == 500_000

    def test_based_on_category(
        self, db_session: Session, engine_ctx: dict
    ) -> None:
        # TVA collectée = 20% des ventes du mois
        # Créer une nouvelle catégorie TVA + line BASED_ON_CATEGORY(base=Ventes, ratio=0.2)
        tva = Category(name="TVA", slug="tva-engine")
        db_session.add(tva)
        db_session.flush()
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=tva.id,
            method=ForecastLineMethod.BASED_ON_CATEGORY,
            base_category_id=engine_ctx["ventes"].id,
            ratio=Decimal("0.2"),
        )
        db_session.add(line)
        db_session.commit()
        # Sur un mois qui a des ventes (M-1), il n'y a pas de forecast car passé
        # On utilise plutôt un mois futur : ratio * ventes_mois_futur (=0)
        # Donc on teste sur current_month : ventes_courant = 0 → tva = 0
        # Mieux : on peut pousser une vente en current_month pour tester.
        # Ici on vérifie juste que la ligne est bien évaluée sans erreur.
        future_month = _add_months(engine_ctx["current_month"], 1)
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=tva.id,
            month=future_month,
        )
        # Pas de ventes dans le mois futur → forecast = 0
        assert cell.forecast_cents == 0

    def test_based_on_category_past_month_historical(
        self, db_session: Session, engine_ctx: dict
    ) -> None:
        """Test explicite : BASED_ON_CATEGORY lue via _evaluate_line à un mois
        où des ventes existent."""
        from app.services.forecast_engine import _evaluate_line

        tva = Category(name="TVA2", slug="tva2-engine")
        db_session.add(tva)
        db_session.flush()
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=tva.id,
            method=ForecastLineMethod.BASED_ON_CATEGORY,
            base_category_id=engine_ctx["ventes"].id,
            ratio=Decimal("0.2"),
        )
        db_session.add(line)
        db_session.commit()
        past_month = _add_months(engine_ctx["current_month"], -3)
        value = _evaluate_line(
            db_session,
            line,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            month=past_month,
        )
        # Ventes mois passé = 500_000 cents, ratio 0.2 → 100_000
        assert value == 100_000


# ---------------------------------------------------------------------------
# FORMULA method
# ---------------------------------------------------------------------------


class TestFormula:
    def test_formula_simple(self, db_session: Session, engine_ctx: dict) -> None:
        # Créer une catégorie "TVA_F" avec formule {Ventes} * 0.2
        tva = Category(name="TVAForm", slug="tva-form-engine")
        db_session.add(tva)
        db_session.flush()
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=tva.id,
            method=ForecastLineMethod.FORMULA,
            formula_expr="{Ventes} * 0.2",
        )
        db_session.add(line)
        db_session.commit()
        # Sur current_month, les ventes sont nulles → tva = 0
        # Sur current_month, via _evaluate_line on teste quand le resolver
        # renvoie la cell de Ventes qui sera realized=0 → total=0
        # Pour obtenir une valeur non-nulle, on ajoute une tx Ventes à current_month
        # puis on recalcule.
        from app.models.bank_account import BankAccount
        ba = engine_ctx["bank_account"]

        # pick the existing import to reuse
        existing_import = db_session.scalars(
            (
                __import__("sqlalchemy").select(ImportRecord).where(
                    ImportRecord.bank_account_id == ba.id
                )
            )
        ).first()
        op_date = engine_ctx["current_month"]
        db_session.add(
            Transaction(
                bank_account_id=ba.id,
                import_id=existing_import.id,
                operation_date=op_date,
                value_date=op_date,
                amount=Decimal("1000.00"),
                label="Vente current",
                raw_label="Vente current",
                dedup_key=f"vente-current-{op_date.isoformat()}",
                statement_row_index=999,
                category_id=engine_ctx["ventes"].id,
                normalized_label="vente current",
            )
        )
        db_session.commit()

        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=tva.id,
            month=engine_ctx["current_month"],
        )
        # Ventes du current_month = 100_000 cents → tva forecast = 20_000
        assert cell.forecast_cents == 20_000

    def test_formula_cycle_raises(
        self, db_session: Session, engine_ctx: dict
    ) -> None:
        # Line FORMULA sur Salaires qui référence Salaires (cycle direct)
        line = ForecastLine(
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["salaires"].id,
            method=ForecastLineMethod.FORMULA,
            formula_expr="{Salaires}",
        )
        db_session.add(line)
        db_session.commit()
        with pytest.raises(FormulaError):
            compute_cell(
                db_session,
                scenario_id=engine_ctx["scenario"].id,
                entity_id=engine_ctx["entity"].id,
                category_id=engine_ctx["salaires"].id,
                month=engine_ctx["current_month"],
            )


# ---------------------------------------------------------------------------
# compute_cell : split mois courant
# ---------------------------------------------------------------------------


class TestCurrentMonthSplit:
    def test_current_month_realized_plus_committed_plus_remaining(
        self, db_session: Session, engine_ctx: dict
    ) -> None:
        """Vérifie realized + committed + max(0, forecast - realized - committed)."""
        e = engine_ctx["entity"]
        sc = engine_ctx["scenario"]
        ventes = engine_ctx["ventes"]
        ba = engine_ctx["bank_account"]

        # Ajoute une tx Ventes réalisée ce mois (+2000€ = 200_000 cents)
        existing_import = db_session.scalars(
            (
                __import__("sqlalchemy").select(ImportRecord).where(
                    ImportRecord.bank_account_id == ba.id
                )
            )
        ).first()
        op_date = engine_ctx["current_month"]
        db_session.add(
            Transaction(
                bank_account_id=ba.id,
                import_id=existing_import.id,
                operation_date=op_date,
                value_date=op_date,
                amount=Decimal("2000.00"),
                label="V currentMO",
                raw_label="V currentMO",
                dedup_key=f"v-curmo-{op_date.isoformat()}",
                statement_row_index=1001,
                category_id=ventes.id,
                normalized_label="v currentmo",
            )
        )
        # Ajoute un commitment PENDING de 100_000 cents (in) ce mois
        db_session.add(
            Commitment(
                entity_id=e.id,
                category_id=ventes.id,
                bank_account_id=ba.id,
                direction=CommitmentDirection.IN,
                amount_cents=100_000,
                issue_date=op_date,
                expected_date=op_date,
                status=CommitmentStatus.PENDING,
            )
        )
        # Forecast RECURRING_FIXED 500_000
        db_session.add(
            ForecastLine(
                scenario_id=sc.id,
                entity_id=e.id,
                category_id=ventes.id,
                method=ForecastLineMethod.RECURRING_FIXED,
                amount_cents=500_000,
            )
        )
        db_session.commit()

        cell = compute_cell(
            db_session,
            scenario_id=sc.id,
            entity_id=e.id,
            category_id=ventes.id,
            month=engine_ctx["current_month"],
        )
        assert cell.realized_cents == 200_000
        assert cell.committed_cents == 100_000
        assert cell.forecast_cents == 500_000
        # total = 200k + 100k + max(0, 500k - 200k - 100k) = 500k
        assert cell.total_cents == 500_000

    def test_past_month_total_is_realized(
        self, db_session: Session, engine_ctx: dict
    ) -> None:
        past = _add_months(engine_ctx["current_month"], -2)
        cell = compute_cell(
            db_session,
            scenario_id=engine_ctx["scenario"].id,
            entity_id=engine_ctx["entity"].id,
            category_id=engine_ctx["salaires"].id,
            month=past,
        )
        assert cell.realized_cents == -300_000
        assert cell.forecast_cents == 0  # pas de forecast passé
        assert cell.total_cents == -300_000


# ---------------------------------------------------------------------------
# compute_pivot (agrégation)
# ---------------------------------------------------------------------------


class TestComputePivot:
    def test_pivot_shape(self, db_session: Session, engine_ctx: dict) -> None:
        sc = engine_ctx["scenario"]
        e = engine_ctx["entity"]
        from_m = _add_months(engine_ctx["current_month"], -2)
        to_m = engine_ctx["current_month"]
        result = compute_pivot(
            db_session,
            scenario_id=sc.id,
            entity_id=e.id,
            from_month=from_m,
            to_month=to_m,
        )
        assert len(result.months) == 3
        # 2 catégories non-vides (Salaires, Ventes)
        labels = {row.label for row in result.rows}
        assert "Salaires" in labels
        assert "Ventes" in labels
        # Directions inférées
        rows_by_label = {r.label: r for r in result.rows}
        assert rows_by_label["Ventes"].direction == "in"
        assert rows_by_label["Salaires"].direction == "out"
        # closing_balance_projection a bien 3 valeurs
        assert len(result.closing_balance_projection_cents) == 3
        # realized_series et forecast_series chacun avec 3 mois
        assert len(result.realized_series) == 3
        assert len(result.forecast_series) == 3
