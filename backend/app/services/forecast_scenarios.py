"""Services autour des scénarios de prévisionnel."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User


def ensure_default_scenario(
    session: Session, entity: Entity, created_by: User | None = None,
) -> ForecastScenario:
    """Garantit qu'une entité a un scénario par défaut ("Principal").

    Idempotent : si un scénario `is_default=True` existe déjà pour l'entité,
    le renvoie tel quel. Sinon en crée un nouveau et l'attache à `entity`.
    L'appelant reste responsable du `session.commit()`.
    """
    existing = session.scalar(
        select(ForecastScenario).where(
            ForecastScenario.entity_id == entity.id,
            ForecastScenario.is_default.is_(True),
        )
    )
    if existing is not None:
        return existing

    scenario = ForecastScenario(
        entity_id=entity.id,
        name="Principal",
        description=None,
        is_default=True,
        created_by_id=created_by.id if created_by is not None else None,
    )
    session.add(scenario)
    session.flush()
    return scenario
