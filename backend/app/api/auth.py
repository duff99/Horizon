from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import COOKIE_NAME
from app.models.user import User
from app.rate_limiter import limiter
from app.schemas.auth import LoginRequest, LoginResponse
from app.security import SessionTokenError, decode_session_token, encode_session_token, verify_password
from app.services.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION_MINUTES = 15


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))

    # Email inconnu : 401 sans info supplémentaire (anti-énumération)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides"
        )

    now = datetime.now(UTC)

    # Compte verrouillé (locked_until dans le futur)
    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(
            status_code=423,
            detail="Compte temporairement verrouillé suite à plusieurs échecs. Réessayez plus tard.",
        )

    # Vérification du mot de passe et du statut
    if not user.is_active or not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=_LOCKOUT_DURATION_MINUTES)
        record_audit(
            db,
            user=user,
            action="login_failed",
            entity=user,
            after={"email": user.email},
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides"
        )

    # Succès : réinitialiser le compteur et tracer
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    token = encode_session_token(
        user_id=user.id,
        version=user.session_token_version,
        secret=settings.secret_key,
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    record_audit(
        db,
        user=user,
        action="login",
        entity=user,
        after={"email": user.email, "role": user.role.value},
        request=request,
    )
    db.commit()
    return LoginResponse(
        id=user.id, email=user.email, role=user.role.value, full_name=user.full_name
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    # Tenter de retrouver l'utilisateur depuis le cookie pour l'audit.
    # Si le cookie est absent/invalide : on déconnecte quand même, sans audit.
    user: User | None = None
    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val:
        try:
            user_id, _version = decode_session_token(
                cookie_val,
                secret=settings.secret_key,
                max_age_seconds=settings.session_hours * 3600,
            )
            user = db.get(User, user_id)
        except (SessionTokenError, Exception):
            pass
    response.delete_cookie(COOKIE_NAME)
    if user is not None:
        record_audit(
            db,
            user=user,
            action="logout",
            entity=user,
            after={"email": user.email},
            request=request,
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
