from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """URL pointant sur une base de test séparée de la base de dev.

    Par convention, on suffixe `_test` à la base principale.
    """
    base = get_settings().database_url
    # Remplace le dernier segment "/nom_base" par "/nom_base_test"
    if "/" not in base:
        raise RuntimeError("DATABASE_URL malformée")
    head, _, name = base.rpartition("/")
    return f"{head}/{name}_test"


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    """Crée un engine vers la base de test et applique les migrations Alembic.

    IMPORTANT : on applique les migrations Alembic (source de vérité), pas
    Base.metadata.create_all(). Cela garantit que les tests exercent
    exactement le schéma qui sera déployé en production.
    """
    from sqlalchemy import text
    from sqlalchemy.engine.url import make_url

    url = make_url(test_database_url)
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": url.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()

    # Exécuter alembic upgrade head contre la base de test
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_database_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_database_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Session de test avec rollback automatique à la fin."""
    connection = test_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
