"""Endpoint POST /api/client-errors — remontée erreurs frontend.

Auth optionnelle : on associe `user_id` si un cookie de session valide est
fourni, mais on accepte aussi les erreurs anonymes (avant login, ou si la
session a expiré). Rate-limité pour éviter qu'un bug en boucle ne sature
la DB.

Le cleanup 30j est géré par un appel manuel (cf. cron horizon-backup) — voir
script `cleanup-client-errors.sh`.
"""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import COOKIE_NAME
from app.models.client_error import ClientError
from app.models.user import User
from app.rate_limiter import limiter
from app.schemas.client_error import ClientErrorCreate
from app.security import SessionTokenError, decode_session_token

router = APIRouter(prefix="/api/client-errors", tags=["client-errors"])


def _try_resolve_user(
    session_cookie: str | None,
    settings: Settings,
    db: Session,
) -> User | None:
    """Essaie de résoudre le user à partir du cookie ; retourne None silencieusement
    si le cookie est absent / invalide / expiré."""
    if not session_cookie:
        return None
    try:
        user_id = decode_session_token(
            session_cookie,
            secret=settings.secret_key,
            max_age_seconds=settings.session_hours * 3600,
        )
    except SessionTokenError:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
def report_client_error(
    request: Request,
    payload: ClientErrorCreate,
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    user = _try_resolve_user(session_cookie, settings, db)
    err = ClientError(
        user_id=user.id if user else None,
        severity=payload.severity,
        source=payload.source,
        message=payload.message,
        stack=payload.stack,
        url=payload.url,
        user_agent=payload.user_agent,
        request_id=payload.request_id,
        context_json=payload.context_json,
    )
    db.add(err)
    db.commit()
