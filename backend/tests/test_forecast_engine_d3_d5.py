"""Tests forecast_engine : D3 (_combine_total) et D5 (AVG guards)."""
from __future__ import annotations
from datetime import date
import pytest
from app.services.forecast_engine import _combine_total

PAST = date(2026, 3, 1)
CURRENT = date(2026, 5, 1)
FUTURE = date(2026, 7, 1)


class TestCombineTotal:
    """D3 — mois futurs doivent inclure committed_pending quand forecast==0."""

    def test_past_returns_realized_only(self):
        assert _combine_total(50_000, 10_000, 30_000, PAST, CURRENT) == 50_000

    def test_future_no_forecast_includes_committed(self):
        """Sans ligne (forecast=0), committed remonte sur mois futur."""
        assert _combine_total(0, -15_000, 0, FUTURE, CURRENT) == -15_000

    def test_future_with_forecast_ignores_committed(self):
        """Avec une ligne (forecast!=0), committed ignoré (choix utilisateur)."""
        assert _combine_total(0, -15_000, -20_000, FUTURE, CURRENT) == -20_000

    def test_current_month_with_remaining(self):
        # remaining = max(0, 20000 - 10000 - 5000) = 5000 → total = 20000
        assert _combine_total(10_000, 5_000, 20_000, CURRENT, CURRENT) == 20_000

    def test_current_month_no_remaining(self):
        # remaining = max(0, 20000 - 18000 - 5000) = 0 → total = 23000
        assert _combine_total(18_000, 5_000, 20_000, CURRENT, CURRENT) == 23_000

    def test_current_month_outflow_forecast_applies(self):
        """Régression : forecast décaissement (négatif) doit s'appliquer sur le
        mois courant, pas être clampé à 0. Bug : Moyenne 3M sur Mai donnait
        une cellule vide alors que Juin/Juillet/... affichaient la valeur."""
        # Pas encore de réalisé, pas de commitments, forecast = -3000 (avg)
        assert _combine_total(0, 0, -300_000, CURRENT, CURRENT) == -300_000

    def test_current_month_outflow_partial_realized(self):
        """Décaissement déjà partiellement réalisé : la prévision reste
        un plancher en magnitude, on garde min(actual, forecast)."""
        # realized = -500 (un loyer déjà payé), forecast = -3000 (prédit avg)
        # actual = -500 ; min(-500, -3000) = -3000 (la prévision domine)
        assert _combine_total(-50_000, 0, -300_000, CURRENT, CURRENT) == -300_000

    def test_current_month_outflow_already_exceeded(self):
        """Si la réalité dépasse déjà la prévision (en magnitude), on
        garde le réel — la prévision ne masque pas la sur-consommation."""
        # realized = -5000, forecast = -3000 ; min(-5000, -3000) = -5000
        assert _combine_total(-500_000, 0, -300_000, CURRENT, CURRENT) == -500_000

    def test_current_month_no_forecast_keeps_outflow_realized(self):
        """Régression : sans ligne (forecast=0), un décaissement réalisé
        doit rester visible (ancien bug : remaining=-realized non clampé
        annulait le réel)."""
        assert _combine_total(-50_000, 0, 0, CURRENT, CURRENT) == -50_000


class TestAvgTransactionsGuard:
    """D5 — division par mois disponibles, pas par N fixe."""

    def test_avg_no_history_returns_zero(self, db_session):
        """Catégorie sans historique → 0 (jamais de division par zéro)."""
        from datetime import date
        from app.services.forecast_engine import _avg_transactions_n_months
        result = _avg_transactions_n_months(
            db_session, entity_id=999999, category_id=999999,
            month=date(2026, 5, 1), n_months=3,
        )
        assert result == 0

    def test_avg_returns_int(self, db_session):
        from datetime import date
        from app.services.forecast_engine import _avg_transactions_n_months
        result = _avg_transactions_n_months(
            db_session, entity_id=999999, category_id=999999,
            month=date(2026, 5, 1), n_months=6,
        )
        assert isinstance(result, int)
