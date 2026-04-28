from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.entity import Entity
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

    Politique d'accès (option C, 2026-04) :
    - Un ADMIN a accès implicite à toutes les entités. Aucune entrée dans
      `user_entity_access` n'est requise pour lui.
    - Un READER n'a accès qu'aux entités explicitement listées dans
      `user_entity_access`.

    Cette politique reflète le fait que les admins de l'instance sont des
    personnes de confiance, déclarées par un autre admin. Donner à un admin
    un compte sans accès aux entités n'a aucun intérêt opérationnel.
    """
    if user.role == UserRole.ADMIN:
        return
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


def accessible_entity_ids_subquery(*, session: Session, user: User) -> Select[tuple[int]]:
    """Sous-requête `SELECT entity_id` filtrée selon les accès du user.

    À utiliser comme `Model.entity_id.in_(accessible_entity_ids_subquery(...))`
    dans les listings.

    Politique miroir de `require_entity_access` :
    - ADMIN → renvoie tous les ids d'entités (`SELECT id FROM entities`).
    - READER → renvoie les ids accessibles (`SELECT entity_id FROM
      user_entity_access WHERE user_id = ?`).

    Le paramètre `session` est conservé pour cohérence d'API et future
    extensibilité (filtrages plus complexes), même si l'implémentation
    actuelle n'en a pas besoin.
    """
    del session  # non utilisé pour l'instant — voir docstring
    if user.role == UserRole.ADMIN:
        return select(Entity.id)
    return select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
