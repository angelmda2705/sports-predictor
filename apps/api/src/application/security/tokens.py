"""Emisión y validación de tokens.

- **Access token:** JWT firmado (HS256) con TTL corto. Lleva el rol/plan para RBAC.
- **Refresh token:** cadena opaca aleatoria de alta entropía. En la base solo se
  guarda su SHA-256 (no el valor), y se rota en cada uso (ver AuthService).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from ...domain.errors import InvalidToken
from ...domain.user import Plan, Role, User


class TokenService:
    """Crea y valida access tokens JWT."""

    def __init__(self, *, secret: str, algorithm: str = "HS256", access_ttl_minutes: int = 15):
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_ttl_minutes)

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._access_ttl.total_seconds())

    def create_access_token(self, user: User) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.id),
            "role": str(user.role),
            "plan": str(user.plan),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> dict[str, object]:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise InvalidToken("Token de acceso inválido o expirado.") from exc
        if claims.get("type") != "access":
            raise InvalidToken("Tipo de token incorrecto.")
        return claims

    @staticmethod
    def parse_role(claims: dict[str, object]) -> Role:
        return Role(str(claims.get("role", Role.USER)))

    @staticmethod
    def parse_plan(claims: dict[str, object]) -> Plan:
        return Plan(str(claims.get("plan", Plan.FREE)))


def new_refresh_token() -> tuple[str, str]:
    """Genera ``(token_en_claro, hash_sha256)``.

    El valor en claro se entrega al cliente una sola vez; en la base se guarda el hash.
    """
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
