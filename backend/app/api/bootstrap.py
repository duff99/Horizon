from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User, UserRole
from app.rate_limiter import limiter
from app.schemas.user import UserCreate, UserRead
from app.security import hash_password, validate_password_policy

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def bootstrap_first_admin(
    request: Request, payload: UserCreate, db: Session = Depends(get_db)
) -> User:
    already = db.scalar(select(User).limit(1))
    if already is not None:
        raise HTTPException(status_code=409, detail="L'amorçage est déjà effectué")
    validate_password_policy(payload.password)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
