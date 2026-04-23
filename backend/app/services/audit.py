"""Service d'audit trail.

Fournit `record_audit()` + `audit_context()` pour instrumenter les mutations.

Design :
- Sync SQLAlchemy (cohérent avec le reste de l'app Horizon).
- `to_dict_for_audit()` sérialise une entité ORM en dict JSON-safe
  (Decimal->str, datetime->isoformat, UUID->str, Enum->.value).
- Les champs sensibles (password_hash, totp_secret, api_token) sont
  masqués à `"<redacted>"` systématiquement.
- `record_audit` ne DOIT JAMAIS faire planter la transaction métier :
  toute exception est loggée et ignorée.
- L'audit vit dans la même transaction que la mutation (même session),
  donc un rollback métier rollback aussi l'audit — cohérent.
"""
from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterator, Literal

from fastapi import Request
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.user import User

logger = logging.getLogger(__name__)

AuditAction = Literal["create", "update", "delete"]

# Ne jamais sérialiser ces champs en clair — masqués en "<redacted>".
_SENSITIVE_FIELDS: set[str] = {
    "password_hash",
    "totp_secret",
    "api_token",
    "api_secret",
    "secret",
}

_REDACTED = "<redacted>"


def _to_json_safe(value: Any) -> Any:
    """Convertit une valeur Python en représentation JSON-safe."""
    if value is None:
        return None
    if isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(v) for v in value]
    # Dernière chance : stringify
    return str(value)


def to_dict_for_audit(entity: Base) -> dict[str, Any]:
    """Sérialise une entité SQLAlchemy en dict JSON-safe.

    - Liste uniquement les colonnes mappées (pas les relations).
    - Masque les champs sensibles.
    - Retourne des types JSON-primitifs (str/int/float/bool/None).
    """
    result: dict[str, Any] = {}
    try:
        mapper = sqla_inspect(entity.__class__)
    except Exception:
        return result
    for col in mapper.columns:
        name = col.key
        if name in _SENSITIVE_FIELDS:
            result[name] = _REDACTED
            continue
        try:
            raw = getattr(entity, name)
        except Exception:
            continue
        result[name] = _to_json_safe(raw)
    return result


def compute_diff(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Calcule les champs changés entre before et after.

    Retourne `{field: {"before": x, "after": y}}` uniquement pour les clés
    dont la valeur a changé. Si l'un des deux est None (create/delete),
    renvoie un dict vide (le before/after lui-même suffit à tracer l'état).
    """
    if before is None or after is None:
        return {}
    diff: dict[str, dict[str, Any]] = {}
    keys = set(before.keys()) | set(after.keys())
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b != a:
            diff[k] = {"before": b, "after": a}
    return diff


def _extract_request_meta(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {"ip_address": None, "user_agent": None, "request_id": None}
    # IP : prend X-Forwarded-For si présent (derrière nginx), sinon client.host
    ip: str | None = None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
    elif request.client is not None:
        ip = request.client.host
    ua = request.headers.get("user-agent")
    if ua is not None:
        ua = ua[:255]
    req_id = request.headers.get("x-request-id")
    if req_id is not None:
        req_id = req_id[:36]
    return {"ip_address": ip, "user_agent": ua, "request_id": req_id}


def _entity_identity(entity: Base) -> tuple[str, str]:
    """Retourne (entity_type, entity_id) pour une entité ORM."""
    entity_type = entity.__class__.__name__
    # Récupère la PK via l'inspector (plus robuste que getattr("id")).
    try:
        mapper = sqla_inspect(entity.__class__)
        pk_cols = [c.key for c in mapper.primary_key]
        if pk_cols:
            raw = getattr(entity, pk_cols[0], None)
        else:
            raw = getattr(entity, "id", None)
    except Exception:
        raw = getattr(entity, "id", None)
    entity_id = "" if raw is None else str(raw)
    return entity_type, entity_id


def record_audit(
    session: Session,
    *,
    user: User | None,
    action: AuditAction,
    entity: Base,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request: Request | None = None,
    entity_type_override: str | None = None,
    entity_id_override: str | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    """Enregistre une ligne d'audit_log.

    N'échoue JAMAIS — toute exception est silencieusement loggée.

    - `before` : dict pré-mutation. None pour create.
    - `after`  : dict post-mutation. None pour delete.
    - `summary` : utilisé pour les mutations batch (ex. import) — stocké tel
      quel dans `after_json` si fourni, avec before=None.
    """
    try:
        entity_type, entity_id = _entity_identity(entity)
        if entity_type_override is not None:
            entity_type = entity_type_override
        if entity_id_override is not None:
            entity_id = entity_id_override

        if summary is not None:
            before_safe = None
            after_safe = _to_json_safe(summary)
        else:
            before_safe = before
            after_safe = after

        diff = compute_diff(before_safe, after_safe) if summary is None else {}

        meta = _extract_request_meta(request)

        row = AuditLog(
            user_id=user.id if user is not None else None,
            user_email=user.email if user is not None else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id or "",
            before_json=before_safe,
            after_json=after_safe,
            diff_json=diff or None,
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
            request_id=meta["request_id"],
        )
        session.add(row)
        # On flush pour remonter immédiatement une erreur éventuelle, mais
        # on commit dans la même transaction que la mutation métier.
        session.flush()
    except Exception as exc:  # noqa: BLE001 — audit NE DOIT JAMAIS planter le métier
        logger.exception("audit.record_failed", extra={"error": str(exc)})


class _AuditContext:
    """Contexte capturé par `audit_context()` — permet d'override l'action/before."""

    __slots__ = ("before", "after", "action")

    def __init__(self) -> None:
        self.before: dict[str, Any] | None = None
        self.after: dict[str, Any] | None = None
        self.action: AuditAction | None = None


@contextmanager
def audit_context(
    session: Session,
    *,
    user: User | None,
    action: AuditAction,
    entity: Base,
    request: Request | None = None,
) -> Iterator[_AuditContext]:
    """Context manager pour wrapper une mutation.

    Usage :
        with audit_context(session, user=u, action="update", entity=tx, request=req):
            tx.category_id = payload.category_id
        session.commit()

    Capture `before` au `__enter__` (snapshot avant mutation), et `after` au
    `__exit__` (via flush pour matérialiser les changements).

    Si `action == "create"` : before=None, after capturé après flush.
    Si `action == "delete"` : before capturé avant, after=None.
    """
    ctx = _AuditContext()
    ctx.action = action

    if action in ("update", "delete"):
        try:
            ctx.before = to_dict_for_audit(entity)
        except Exception:
            ctx.before = None

    try:
        yield ctx
    except Exception:
        # En cas d'exception dans le bloc métier, on ne loggue RIEN et on
        # laisse l'exception se propager (le rollback métier suivra).
        raise

    # Post-mutation : capturer after si applicable.
    try:
        if ctx.action in ("create", "update"):
            # Flush pour matérialiser les mutations (id auto, onupdate triggers, etc.)
            session.flush()
            ctx.after = to_dict_for_audit(entity)
    except Exception:
        ctx.after = None

    # Override possible via ctx.action (ex. update dégénéré en noop)
    final_action: AuditAction = ctx.action or action
    record_audit(
        session,
        user=user,
        action=final_action,
        entity=entity,
        before=ctx.before,
        after=ctx.after,
        request=request,
    )
