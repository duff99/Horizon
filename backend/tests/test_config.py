import pytest

from app.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")
    monkeypatch.setenv("BACKEND_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:5173")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.database_url == "postgresql+psycopg://u:p@localhost/x"
    assert settings.secret_key == "a" * 32
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_rejects_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")
    monkeypatch.setenv("BACKEND_SECRET_KEY", "too_short")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:5173")

    with pytest.raises(ValueError, match="32 caractères"):
        Settings()  # type: ignore[call-arg]
