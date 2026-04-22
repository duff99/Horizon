"""Tests Pydantic pour les schémas forecast v2 (Plan 5b Phase 3)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.forecast import (
    ForecastMethod,
    LineUpsert,
    ScenarioCreate,
    ScenarioUpdate,
)


class TestScenarioSchemas:
    def test_create_defaults(self) -> None:
        s = ScenarioCreate(entity_id=1, name="Principal")
        assert s.is_default is False
        assert s.description is None

    def test_create_explicit_default(self) -> None:
        s = ScenarioCreate(entity_id=1, name="Alt", is_default=True, description="x")
        assert s.is_default is True
        assert s.description == "x"

    def test_create_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            ScenarioCreate(entity_id=1, name="")

    def test_update_all_optional(self) -> None:
        s = ScenarioUpdate()
        assert s.model_dump(exclude_unset=True) == {}

    def test_update_partial(self) -> None:
        s = ScenarioUpdate(is_default=True)
        assert s.is_default is True
        assert s.name is None


class TestLineUpsertValidation:
    def test_recurring_fixed_ok(self) -> None:
        line = LineUpsert(
            scenario_id=1,
            category_id=2,
            method=ForecastMethod.RECURRING_FIXED,
            amount_cents=50_000,
        )
        assert line.amount_cents == 50_000

    def test_recurring_fixed_requires_amount(self) -> None:
        with pytest.raises(ValidationError) as exc:
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.RECURRING_FIXED,
            )
        assert "RECURRING_FIXED requires amount_cents" in str(exc.value)

    def test_based_on_category_requires_both(self) -> None:
        with pytest.raises(ValidationError):
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.BASED_ON_CATEGORY,
                base_category_id=3,
            )
        with pytest.raises(ValidationError):
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.BASED_ON_CATEGORY,
                ratio=Decimal("0.5"),
            )

    def test_based_on_category_ok(self) -> None:
        line = LineUpsert(
            scenario_id=1,
            category_id=2,
            method=ForecastMethod.BASED_ON_CATEGORY,
            base_category_id=5,
            ratio=Decimal("0.2"),
        )
        assert line.base_category_id == 5
        assert line.ratio == Decimal("0.2")

    def test_ratio_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.BASED_ON_CATEGORY,
                base_category_id=5,
                ratio=Decimal("0"),
            )

    def test_ratio_upper_bound(self) -> None:
        with pytest.raises(ValidationError):
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.BASED_ON_CATEGORY,
                base_category_id=5,
                ratio=Decimal("11"),
            )

    def test_formula_requires_expression(self) -> None:
        with pytest.raises(ValidationError) as exc:
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.FORMULA,
            )
        assert "FORMULA requires formula_expr" in str(exc.value)

    def test_formula_ok(self) -> None:
        line = LineUpsert(
            scenario_id=1,
            category_id=2,
            method=ForecastMethod.FORMULA,
            formula_expr="cat(3) * 0.5",
        )
        assert line.formula_expr == "cat(3) * 0.5"

    def test_stats_methods_accept_no_extra_params(self) -> None:
        for m in (
            ForecastMethod.AVG_3M,
            ForecastMethod.AVG_6M,
            ForecastMethod.AVG_12M,
            ForecastMethod.PREVIOUS_MONTH,
            ForecastMethod.SAME_MONTH_LAST_YEAR,
        ):
            line = LineUpsert(scenario_id=1, category_id=2, method=m)
            assert line.method == m

    def test_start_end_month_ordering(self) -> None:
        with pytest.raises(ValidationError):
            LineUpsert(
                scenario_id=1,
                category_id=2,
                method=ForecastMethod.AVG_3M,
                start_month=date(2026, 6, 1),
                end_month=date(2026, 3, 1),
            )

    def test_method_mirror_values(self) -> None:
        """Le miroir Pydantic doit avoir exactement les mêmes valeurs que le modèle."""
        from app.models.forecast_line import ForecastLineMethod

        assert {m.value for m in ForecastMethod} == {
            m.value for m in ForecastLineMethod
        }
