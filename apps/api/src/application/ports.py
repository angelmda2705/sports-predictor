"""Puertos (interfaces) de persistencia para el subsistema de auth.

La capa de aplicación depende solo de estos protocolos; las implementaciones
concretas (en memoria, SQLAlchemy) viven en infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ..domain.user import User


@dataclass
class RefreshTokenRecord:
    """Registro de un refresh token. Se guarda el HASH del token, nunca el valor."""

    id: int | None
    user_id: int
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    rotated_from: int | None = None


class UserRepository(Protocol):
    def add(self, user: User) -> User:
        """Persiste un usuario nuevo y devuelve la entidad con ``id`` asignado."""
        ...

    def get_by_email(self, email: str) -> User | None: ...

    def get_by_id(self, user_id: int) -> User | None: ...


class RefreshTokenRepository(Protocol):
    def add(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        rotated_from: int | None = None,
    ) -> RefreshTokenRecord: ...

    def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None: ...

    def revoke(self, token_id: int, *, when: datetime) -> None: ...

    def revoke_all_for_user(self, user_id: int, *, when: datetime) -> None:
        """Revoca todos los tokens vivos del usuario (detección de reuso)."""
        ...
