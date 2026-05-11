from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.entity import Entity
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.schemas.user import (
    AdminPasswordResetPayload,
    EntityAccessGrant,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.security import hash_password, validate_password_policy
from app.services.audit import record_audit, to_dict_for_audit

router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)]
)

_USER_UPDATABLE_FIELDS = {"role", "full_name", "is_active"}


def _would_leave_no_active_admin(
    db: Session,
    *,
    user: User,
    next_role: UserRole | None,
    next_active: bool | None,
) -> bool:
    """True si la mise à jour proposée retire le dernier admin actif."""
    effective_role = next_role if next_role is not None else user.role
    effective_active = next_active if next_active is not None else user.is_active
    if effective_role == UserRole.ADMIN and effective_active:
        return False
    others = db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.id != user.id,
        )
    )
    return (others or 0) == 0


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> User:
    validate_password_policy(payload.password)
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()
    record_audit(
        db, user=current, action="create", entity=user,
        before=None, after=to_dict_for_audit(user), request=request,
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    data = payload.model_dump(exclude_unset=True)
    if _would_leave_no_active_admin(
        db,
        user=user,
        next_role=data.get("role"),
        next_active=data.get("is_active"),
    ):
        raise HTTPException(
            status_code=409,
            detail="Impossible : cette opération laisserait le système sans administrateur actif",
        )
    before_snapshot = to_dict_for_audit(user)
    for field, value in data.items():
        if field in _USER_UPDATABLE_FIELDS:
            setattr(user, field, value)
    db.flush()
    record_audit(
        db, user=current, action="update", entity=user,
        before=before_snapshot, after=to_dict_for_audit(user), request=request,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordResetPayload,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> None:
    """Admin reset : définit un nouveau mot de passe pour n'importe quel user."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    new_pw = payload.new_password.get_secret_value()
    try:
        validate_password_policy(new_pw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    # Audit : before/after masqués (password_hash filtré par _SENSITIVE_FIELDS),
    # mais on trace tout de même l'action.
    before_snapshot = to_dict_for_audit(user)
    user.password_hash = hash_password(new_pw)
    user.session_token_version = (user.session_token_version or 1) + 1
    db.flush()
    record_audit(
        db, user=current, action="update", entity=user,
        before=before_snapshot, after=to_dict_for_audit(user), request=request,
    )
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> None:
    """Désactivation logique uniquement (pas de delete physique)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if _would_leave_no_active_admin(db, user=user, next_role=None, next_active=False):
        raise HTTPException(
            status_code=409,
            detail="Impossible : cette opération laisserait le système sans administrateur actif",
        )
    before_snapshot = to_dict_for_audit(user)
    user.is_active = False
    db.flush()
    # Désactivation logique = update (is_active: true -> false)
    record_audit(
        db, user=current, action="update", entity=user,
        before=before_snapshot, after=to_dict_for_audit(user), request=request,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Entity access (grant / revoke / list) — HIGH-01
# ---------------------------------------------------------------------------


@router.get("/{user_id}/entity-access", response_model=list[int])
def list_user_entity_access(
    user_id: int,
    db: Session = Depends(get_db),
) -> list[int]:
    """IDs des entités auxquelles le user a un accès explicite (table user_entity_access).

    Pour les admins, cette liste est typiquement vide : ils voient toutes les
    entités via leur rôle, pas via user_entity_access.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return list(
        db.scalars(
            select(UserEntityAccess.entity_id).where(UserEntityAccess.user_id == user_id)
        )
    )


@router.post("/{user_id}/entity-access", status_code=status.HTTP_201_CREATED)
def grant_user_entity_access(
    user_id: int,
    payload: EntityAccessGrant,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> dict[str, int]:
    """Accorde à un user l'accès à une entité. Idempotent : 409 si déjà accordé."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    entity = db.get(Entity, payload.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entité introuvable")
    existing = db.scalar(
        select(UserEntityAccess).where(
            UserEntityAccess.user_id == user_id,
            UserEntityAccess.entity_id == payload.entity_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Accès déjà accordé")
    access = UserEntityAccess(user_id=user_id, entity_id=payload.entity_id)
    db.add(access)
    db.flush()
    record_audit(
        db, user=current, action="create", entity=access,
        before=None, after=to_dict_for_audit(access), request=request,
    )
    db.commit()
    db.refresh(access)
    return {"id": access.id, "user_id": access.user_id, "entity_id": access.entity_id}


@router.delete(
    "/{user_id}/entity-access/{entity_id}", status_code=status.HTTP_204_NO_CONTENT
)
def revoke_user_entity_access(
    user_id: int,
    entity_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> None:
    """Révoque l'accès d'un user à une entité."""
    access = db.scalar(
        select(UserEntityAccess).where(
            UserEntityAccess.user_id == user_id,
            UserEntityAccess.entity_id == entity_id,
        )
    )
    if access is None:
        raise HTTPException(status_code=404, detail="Accès introuvable")
    before_snapshot = to_dict_for_audit(access)
    db.delete(access)
    db.flush()
    record_audit(
        db, user=current, action="delete", entity=access,
        before=before_snapshot, after=None, request=request,
    )
    db.commit()
