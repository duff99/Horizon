from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserRead)
def me(current: User = Depends(get_current_user)) -> User:
    return current
