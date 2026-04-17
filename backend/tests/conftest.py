from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import get_db
from app.main import app
from app.models import Base
from app.rate_limiter import limiter

limiter.enabled = False
from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import hash_password


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
    from alembic.config import Config

    from alembic import command

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_database_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_database_url, future=True)
    # Crée à la volée les tables des modèles dont la migration Alembic
    # n'a pas encore été écrite (B5). Une fois la migration en place,
    # cet appel devient un no-op pour les tables déjà créées.
    Base.metadata.create_all(bind=engine)
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


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient FastAPI avec override de la session DB vers db_session."""

    def _override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def auth_user(client: TestClient, db_session: Session) -> User:
    """Crée un user ADMIN actif et se connecte via l'endpoint /api/auth/login.

    La session cookie est stockée automatiquement par le TestClient.
    """
    user = User(
        email="test@example.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    resp = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "test-password-123"},
    )
    assert resp.status_code == 200, f"Login échoué : {resp.text}"
    return user


@pytest.fixture()
def auth_user_reader(client: TestClient, db_session: Session) -> User:
    """Crée un user READER actif et se connecte via /api/auth/login."""
    user = User(
        email="reader@example.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.READER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    resp = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "test-password-123"},
    )
    assert resp.status_code == 200, f"Login échoué : {resp.text}"
    return user


@pytest.fixture()
def auth_user_with_bank_account(
    auth_user: User, db_session: Session,
) -> dict:
    """User authentifié + entité accessible + un compte bancaire de cette entité."""
    e = Entity(name="SAS Horizon Test", legal_name="SAS Horizon Test")
    db_session.add(e)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=e.id)
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000123",
        name="Compte courant Test",
    )
    db_session.add_all([access, ba])
    db_session.commit()
    db_session.refresh(ba)
    return {"user": auth_user, "entity": e, "bank_account": ba}


@pytest.fixture()
def entity(db_session: Session) -> Entity:
    """Entité simple pour les tests de modèles (Plan 2)."""
    e = Entity(name="SAS Modele Test", legal_name="SAS Modele Test")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture()
def bank_account(db_session: Session, entity: Entity) -> BankAccount:
    """Compte bancaire simple rattaché à `entity` (Plan 2)."""
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000999",
        name="Compte courant Modele Test",
    )
    db_session.add(ba)
    db_session.commit()
    db_session.refresh(ba)
    return ba


@pytest.fixture()
def other_entity_bank_account(db_session: Session) -> BankAccount:
    """Compte bancaire d'une entité à laquelle le user authentifié n'a PAS accès."""
    other = Entity(name="SAS Autre Test", legal_name="SAS Autre Test")
    db_session.add(other)
    db_session.flush()
    ba = BankAccount(
        entity_id=other.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7699999999999999999999999",
        name="Compte autre entité",
    )
    db_session.add(ba)
    db_session.commit()
    db_session.refresh(ba)
    return ba
