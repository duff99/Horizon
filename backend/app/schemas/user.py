from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    full_name: str | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    role: UserRole = UserRole.READER
    full_name: str | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    full_name: str | None = None
    is_active: bool | None = None
