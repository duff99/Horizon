"""Helper pour les audit logs batch (1 ligne par opération de masse).

Diffère de record_audit() qui prend une entité ORM : ici on enregistre
une entrée audit construite à la main (entity_type/entity_id virtuels,
ex. 'bulk(N)' ou 'rule-apply(K)').

Garantie : ne fait JAMAIS planter la transaction métier — exception
loggée à WARNING avec exc_info, et drapeau retourné pour visibilité.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.audit import _extract_request_meta

logger = logging.getLogger(__name__)


def record_batch_audit(
    session: Session,
    *,
    user: User,
    request: Request,
    action: str,
    entity_type: str,
    entity_id: str,
    after: dict[str, Any],
    before: dict[str, Any] | None = None,
) -> bool:
    try:
        meta = _extract_request_meta(request)
        session.add(
            AuditLog(
                user_id=user.id,
                user_email=user.email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_json=before,
                after_json=after,
                diff_json=None,
                ip_address=meta["ip_address"],
                user_agent=meta["user_agent"],
                request_id=meta["request_id"],
            )
        )
        session.flush()
        return True
    except Exception:
        logger.warning(
            "audit.batch_failed",
            extra={
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            exc_info=True,
        )
        return False
