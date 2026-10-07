"""Entidad de usuario y enumeraciones de rol/plan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Role(StrEnum):
    """Rol para control de acceso (RBAC)."""

    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"


class Plan(StrEnum):
    """Plan de suscripción del usuario."""

    FREE = "free"
    PRO = "pro"
    ANALYST = "analyst"


@dataclass
class User:
    """Usuario de la plataforma.

    ``password_hash`` guarda SIEMPRE un hash Argon2id, nunca la contraseña en claro.
    ``deleted_at`` implementa soft-delete (derecho al olvido).
    """

    id: int | None
    email: str
    password_hash: str
    role: Role = Role.USER
    plan: Plan = Plan.FREE
    email_verified: bool = False
    created_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normaliza el email para comparaciones case-insensitive consistentes."""
        return email.strip().lower()
