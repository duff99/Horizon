"""Tests du parser DSL de formules (Plan 5b Phase 4.1)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.entity import Entity
from app.models.forecast_line import ForecastLine, ForecastLineMethod
from app.models.forecast_scenario import ForecastScenario
from app.services.formula_parser import (
    BinOp,
    FormulaError,
    Num,
    Ref,
    UnaryOp,
    detect_cycle,
    evaluate,
    extract_refs,
    parse,
)


class TestParseNumbers:
    def test_integer(self) -> None:
        node = parse("5")
        assert isinstance(node, Num)
        assert node.value == Decimal("5")

    def test_decimal(self) -> None:
        node = parse("5.5")
        assert isinstance(node, Num)
        assert node.value == Decimal("5.5")

    def test_negative(self) -> None:
        node = parse("-3")
        assert isinstance(node, UnaryOp)
        assert node.op == "-"
        assert isinstance(node.operand, Num)
        assert node.operand.value == Decimal("3")


class TestParseRefs:
    def test_simple_ref(self) -> None:
        node = parse("{Ventes}")
        assert isinstance(node, Ref)
        assert node.category_name == "ventes"
        assert node.month_offset == 0

    def test_ref_with_offset(self) -> None:
        node = parse("{Salaires_M-12}")
        assert isinstance(node, Ref)
        assert node.category_name == "salaires"
        assert node.month_offset == 12

    def test_ref_case_insensitive(self) -> None:
        node = parse("{VENTES}")
        assert isinstance(node, Ref)
        assert node.category_name == "ventes"

    def test_ref_with_spaces_stripped(self) -> None:
        node = parse("{  Ventes Boutique  }")
        assert isinstance(node, Ref)
        assert node.category_name == "ventes boutique"

    def test_ref_with_accents(self) -> None:
        node = parse("{Intérêts}")
        assert isinstance(node, Ref)
        assert node.category_name == "intérêts"


class TestParseOperators:
    def test_multiplication(self) -> None:
        node = parse("{Ventes} * 0.2")
        assert isinstance(node, BinOp)
        assert node.op == "*"

    def test_parens_and_division(self) -> None:
        node = parse("({A} + {B}) / 2")
        assert isinstance(node, BinOp)
        assert node.op == "/"
        assert isinstance(node.left, BinOp)
        assert node.left.op == "+"

    def test_precedence_mul_over_add(self) -> None:
        node = parse("1 + 2 * 3")
        assert isinstance(node, BinOp)
        assert node.op == "+"
        assert isinstance(node.right, BinOp)
        assert node.right.op == "*"

    def test_subtraction(self) -> None:
        node = parse("{A} - {B}")
        assert isinstance(node, BinOp)
        assert node.op == "-"


class TestParseInvalid:
    def test_empty(self) -> None:
        with pytest.raises(FormulaError):
            parse("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(FormulaError):
            parse("   ")

    def test_unclosed_brace(self) -> None:
        with pytest.raises(FormulaError):
            parse("{")

    def test_empty_ref(self) -> None:
        with pytest.raises(FormulaError):
            parse("{}")

    def test_trailing_operator(self) -> None:
        with pytest.raises(FormulaError):
            parse("5 +")

    def test_double_operator(self) -> None:
        # {A} ++ → {A} + (+??) : le 2e + n'a pas d'operand → fail
        with pytest.raises(FormulaError):
            parse("{A} ++")

    def test_unclosed_paren(self) -> None:
        with pytest.raises(FormulaError):
            parse("(5 + 3")

    def test_unknown_char(self) -> None:
        with pytest.raises(FormulaError):
            parse("5 @ 3")


class TestEvaluate:
    def test_num(self) -> None:
        node = parse("5.5")
        result = evaluate(node, lambda n, o: Decimal("0"))
        assert result == Decimal("5.5")

    def test_ref_resolved(self) -> None:
        node = parse("{Ventes}")
        result = evaluate(node, lambda n, o: Decimal("500000"))
        assert result == Decimal("500000")

    def test_arithmetic(self) -> None:
        node = parse("{Ventes} * 0.2")

        def resolver(name: str, offset: int) -> Decimal:
            return Decimal("500000") if name == "ventes" else Decimal("0")

        result = evaluate(node, resolver)
        assert result == Decimal("100000.0")

    def test_parens(self) -> None:
        node = parse("({A} + {B}) / 2")

        def resolver(name: str, offset: int) -> Decimal:
            return {"a": Decimal("10"), "b": Decimal("30")}[name]

        result = evaluate(node, resolver)
        assert result == Decimal("20")

    def test_division_by_zero(self) -> None:
        node = parse("{A} / {B}")
        with pytest.raises(FormulaError):
            evaluate(node, lambda n, o: Decimal("0"))

    def test_unary_minus(self) -> None:
        node = parse("-{A}")
        result = evaluate(node, lambda n, o: Decimal("42"))
        assert result == Decimal("-42")

    def test_offset_passed_to_resolver(self) -> None:
        node = parse("{Ventes_M-3}")
        captured: dict = {}

        def resolver(name: str, offset: int) -> Decimal:
            captured["name"] = name
            captured["offset"] = offset
            return Decimal("1")

        evaluate(node, resolver)
        assert captured == {"name": "ventes", "offset": 3}


class TestExtractRefs:
    def test_empty_when_num(self) -> None:
        assert extract_refs(parse("5")) == []

    def test_multiple_refs(self) -> None:
        refs = extract_refs(parse("{A} + {B_M-1} * {A}"))
        assert len(refs) == 3
        names = [r.category_name for r in refs]
        assert names.count("a") == 2
        assert "b" in names

    def test_offset_captured(self) -> None:
        refs = extract_refs(parse("{X_M-12}"))
        assert len(refs) == 1
        assert refs[0].month_offset == 12


class TestDetectCycle:
    def _setup(self, db_session: Session, *, formulas: dict[str, str]) -> dict:
        """Crée une entité, un scénario, et pour chaque (cat_name, formula_expr)
        une catégorie + une ForecastLine FORMULA.
        """
        e = Entity(name="CycleTest", legal_name="CycleTest")
        db_session.add(e)
        db_session.flush()
        sc = ForecastScenario(entity_id=e.id, name="S", is_default=True)
        db_session.add(sc)
        db_session.flush()
        cats: dict[str, Category] = {}
        for name in formulas:
            c = Category(name=name, slug=f"cycle-{name.lower()}")
            db_session.add(c)
            cats[name] = c
        db_session.flush()
        for name, expr in formulas.items():
            db_session.add(
                ForecastLine(
                    scenario_id=sc.id,
                    entity_id=e.id,
                    category_id=cats[name].id,
                    method=ForecastLineMethod.FORMULA,
                    formula_expr=expr,
                )
            )
        db_session.commit()
        return {"entity": e, "scenario": sc, "cats": cats}

    def test_no_cycle_simple(self, db_session: Session) -> None:
        ctx = self._setup(db_session, formulas={"Sales": "100"})
        cycle = detect_cycle(
            scenario_id=ctx["scenario"].id,
            target_category_id=ctx["cats"]["Sales"].id,
            formula_expr="100 + 50",
            session=db_session,
        )
        assert cycle is False

    def test_direct_self_reference(self, db_session: Session) -> None:
        ctx = self._setup(db_session, formulas={"Salaires": "{Salaires} * 2"})
        # Valider la formule pour Salaires elle-même → direct cycle
        cycle = detect_cycle(
            scenario_id=ctx["scenario"].id,
            target_category_id=ctx["cats"]["Salaires"].id,
            formula_expr="{Salaires} * 2",
            session=db_session,
        )
        assert cycle is True

    def test_transitive_cycle(self, db_session: Session) -> None:
        # A → B, B → A. Valider une formule pour A qui référence B → cycle
        ctx = self._setup(
            db_session,
            formulas={"CatA": "{CatB}", "CatB": "{CatA}"},
        )
        cycle = detect_cycle(
            scenario_id=ctx["scenario"].id,
            target_category_id=ctx["cats"]["CatA"].id,
            formula_expr="{CatB}",
            session=db_session,
        )
        assert cycle is True

    def test_unknown_ref_ignored(self, db_session: Session) -> None:
        # Ref vers une catégorie qui n'existe pas → pas un cycle (sera rejeté
        # à l'évaluation, mais ici on ne dit pas "cycle")
        ctx = self._setup(db_session, formulas={"Marge": "100"})
        cycle = detect_cycle(
            scenario_id=ctx["scenario"].id,
            target_category_id=ctx["cats"]["Marge"].id,
            formula_expr="{CategorieInexistante}",
            session=db_session,
        )
        assert cycle is False
