from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    secret_key: str = Field(..., alias="BACKEND_SECRET_KEY")
    session_hours: int = Field(8, alias="BACKEND_SESSION_HOURS")
    cors_origins_raw: str = Field(..., alias="BACKEND_CORS_ORIGINS")
    # True en prod (cookie envoyé uniquement en HTTPS), False en dev local.
    cookie_secure: bool = Field(True, alias="BACKEND_COOKIE_SECURE")

    @field_validator("secret_key")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("BACKEND_SECRET_KEY doit contenir au moins 32 caractères")
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


def get_settings() -> Settings:
    """Point d'accès paresseux (testable)."""
    return Settings()  # type: ignore[call-arg]
