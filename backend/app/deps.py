from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import SessionTokenError, decode_session_token

COOKIE_NAME = "session"


def get_current_user(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> User:
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié"
        )
    try:
        user_id = decode_session_token(
            session,
            secret=settings.secret_key,
            max_age_seconds=settings.session_hours * 3600,
        )
    except SessionTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur inconnu ou désactivé",
        )
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    if current.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis",
        )
    return current


def require_entity_access(*, session: Session, user: User, entity_id: int) -> None:
    """Vérifie que l'utilisateur a un accès à l'entité, sinon lève 403.

    Le contrôle d'accès est basé exclusivement sur la table
    `user_entity_access`. Les rôles (ADMIN/READER) régissent d'autres
    permissions (administration globale, écriture) mais ne confèrent pas
    d'accès implicite à toutes les entités.
    """
    has_access = session.execute(
        select(UserEntityAccess.id).where(
            UserEntityAccess.user_id == user.id,
            UserEntityAccess.entity_id == entity_id,
        )
    ).scalar_one_or_none()
    if has_access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à cette entité",
        )
