from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.user import User, UserRole
from app.schemas.user import (
    AdminPasswordResetPayload,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.security import hash_password, validate_password_policy
from app.services.audit import record_audit, to_dict_for_audit

router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)]
)


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
