from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # `str` (et non `EmailStr`) en sortie : les emails sont déjà validés à
    # l'insertion (UserCreate). Si la DB contient une valeur "exotique" (TLD
    # `.local` réservé, ancien import, etc.), on doit pouvoir l'afficher au
    # lieu de 500. Incident 2026-05-12 : user `reader.test@horizon.local` →
    # ResponseValidationError sur `GET /api/users`.
    email: str
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


class PasswordChangePayload(BaseModel):
    current_password: SecretStr
    new_password: SecretStr = Field(min_length=12)


class AdminPasswordResetPayload(BaseModel):
    new_password: SecretStr = Field(min_length=12)


class EntityAccessGrant(BaseModel):
    entity_id: int
