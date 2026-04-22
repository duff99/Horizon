from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import PasswordChangePayload, UserRead
from app.security import hash_password, validate_password_policy, verify_password

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserRead)
def me(current: User = Depends(get_current_user)) -> User:
    return current


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangePayload,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Change le mot de passe de l'utilisateur authentifié."""
    current_pw = payload.current_password.get_secret_value()
    new_pw = payload.new_password.get_secret_value()

    if not verify_password(current_pw, current.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )

    try:
        validate_password_policy(new_pw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    current.password_hash = hash_password(new_pw)
    db.commit()
