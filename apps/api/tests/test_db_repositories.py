"""Integración de los repositorios SQLAlchemy contra SQLite en memoria.

Prueba que el MISMO AuthService funciona con persistencia real (ORM), no solo con
los repos en memoria. SQLite no requiere driver externo, así que corre en cualquier
entorno. Caveat: se opera dentro de una sola sesión (unidad de trabajo por request),
igual que en producción; los timestamptz mantienen tz-awareness en la sesión activa.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.application.auth_service import AuthService
from src.application.security.password import Argon2PasswordHasher
from src.application.security.tokens import TokenService
from src.domain.errors import EmailAlreadyRegistered, InvalidCredentials
from src.infrastructure.db.models import Base
from src.infrastructure.db.repositories import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _service(session: Session) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        hasher=Argon2PasswordHasher(),
        tokens=TokenService(secret="test-secret"),
        refresh_ttl_days=7,
    )


def test_register_and_login_through_orm(session: Session) -> None:
    service = _service(session)
    user = service.register(email="db@example.com", password="password123")
    assert user.id is not None
    assert user.email == "db@example.com"

    pair = service.login(email="db@example.com", password="password123")
    assert pair.access_token and pair.refresh_token


def test_duplicate_email_raises(session: Session) -> None:
    service = _service(session)
    service.register(email="dup@example.com", password="password123")
    with pytest.raises(EmailAlreadyRegistered):
        service.register(email="dup@example.com", password="password123")


def test_wrong_password_raises(session: Session) -> None:
    service = _service(session)
    service.register(email="x@example.com", password="password123")
    with pytest.raises(InvalidCredentials):
        service.login(email="x@example.com", password="nope-nope-nope")


def test_refresh_rotation_persists_in_db(session: Session) -> None:
    service = _service(session)
    service.register(email="rot@example.com", password="password123")
    r1 = service.login(email="rot@example.com", password="password123").refresh_token
    pair2 = service.refresh(refresh_token=r1)
    assert pair2.refresh_token != r1
