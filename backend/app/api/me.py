from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import COOKIE_NAME, get_current_user
from app.models.user import User
from app.schemas.user import PasswordChangePayload, UserRead
from app.security import (
    encode_session_token,
    hash_password,
    validate_password_policy,
    verify_password,
)

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserRead)
def me(current: User = Depends(get_current_user)) -> User:
    return current


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangePayload,
    response: Response,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
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
    # Révoque toutes les sessions actives (y compris cookies volés) en bumpant
    # la version du token. La session courante est immédiatement réémise avec
    # la nouvelle version pour éviter de déconnecter l'utilisateur qui vient
    # de changer son mot de passe.
    current.session_token_version = (current.session_token_version or 1) + 1
    db.commit()

    new_token = encode_session_token(
        user_id=current.id,
        version=current.session_token_version,
        secret=settings.secret_key,
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=new_token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
