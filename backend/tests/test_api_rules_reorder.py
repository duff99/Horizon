"""POST /api/rules/reorder."""
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)


def test_reorder_updates_priorities(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = Category(name="c", slug="c-api-reord", is_system=False)
    db_session.add(cat); db_session.commit()
    r1 = CategorizationRule(
        name="A", priority=9000, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="A",
        category_id=cat.id,
    )
    r2 = CategorizationRule(
        name="B", priority=9100, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="B",
        category_id=cat.id,
    )
    db_session.add_all([r1, r2]); db_session.commit()

    r = client.post("/api/rules/reorder", json=[
        {"id": r1.id, "priority": 99001},
        {"id": r2.id, "priority": 99000},
    ])
    assert r.status_code == 200, r.text
    db_session.refresh(r1); db_session.refresh(r2)
    assert r1.priority == 99001
    assert r2.priority == 99000
