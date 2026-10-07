"""Fixtures compartidas: app con repos en memoria, cliente HTTP y semilla de admin."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.application.security.password import Argon2PasswordHasher
from src.config import Settings
from src.domain.user import Plan, Role, User
from src.infrastructure.memory.repositories import (
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
)
from src.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret="test-secret-please-change", app_env="test")


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def refresh_repo() -> InMemoryRefreshTokenRepository:
    return InMemoryRefreshTokenRepository()


@pytest.fixture
def client(settings, user_repo, refresh_repo) -> TestClient:
    app = create_app(settings=settings, user_repo=user_repo, refresh_repo=refresh_repo)
    return TestClient(app)


@pytest.fixture
def seed_admin(user_repo) -> Callable[..., tuple[str, str]]:
    """Inserta un admin directamente en el repo (no hay endpoint para crear admins)."""

    def _seed(
        email: str = "admin@example.com", password: str = "admin-pass-123"
    ) -> tuple[str, str]:
        hasher = Argon2PasswordHasher()
        user_repo.add(
            User(
                id=None,
                email=User.normalize_email(email),
                password_hash=hasher.hash(password),
                role=Role.ADMIN,
                plan=Plan.PRO,
                created_at=datetime.now(UTC),
            )
        )
        return email, password

    return _seed
