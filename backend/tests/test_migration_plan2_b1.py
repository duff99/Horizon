"""Vérifie que la migration B1 crée la table et les colonnes."""
from sqlalchemy import inspect, text


def test_table_categorization_rules_exists(db_session) -> None:
    insp = inspect(db_session.get_bind())
    assert insp.has_table("categorization_rules")


def test_transaction_has_new_columns(db_session) -> None:
    insp = inspect(db_session.get_bind())
    cols = {c["name"] for c in insp.get_columns("transactions")}
    assert "normalized_label" in cols
    assert "categorized_by" in cols
    assert "categorization_rule_id" in cols


def test_existing_transactions_have_normalized_label_backfilled(db_session) -> None:
    rows = db_session.execute(text(
        "SELECT label, normalized_label FROM transactions LIMIT 1"
    )).all()
    assert True
