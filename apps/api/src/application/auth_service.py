"""Servicio de aplicación de autenticación.

Orquesta los casos de uso de auth contra los puertos de persistencia. No conoce
HTTP ni la base de datos concreta. La rotación de refresh tokens con detección de
reuso es el punto de seguridad central:

- Cada ``refresh`` invalida el token usado y emite uno nuevo (``rotated_from``).
- Si llega un token YA rotado (revocado), se asume robo: se revoca toda la cadena
  del usuario y se rechaza la operación.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..domain.errors import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    TokenReused,
    UserNotFound,
)
from ..domain.user import Plan, Role, User
from .ports import RefreshTokenRepository, UserRepository
from .security.password import PasswordHasher
from .security.tokens import TokenService, hash_refresh_token, new_refresh_token


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int  # segundos de vida del access token


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        refresh_ttl_days: int = 7,
    ) -> None:
        self._users = users
        self._refresh = refresh_tokens
        self._hasher = hasher
        self._tokens = tokens
        self._refresh_ttl = timedelta(days=refresh_ttl_days)

    # --- Registro ---------------------------------------------------------
    def register(
        self, *, email: str, password: str, role: Role = Role.USER, plan: Plan = Plan.FREE
    ) -> User:
        normalized = User.normalize_email(email)
        if self._users.get_by_email(normalized) is not None:
            raise EmailAlreadyRegistered("El email ya está registrado.")
        user = User(
            id=None,
            email=normalized,
            password_hash=self._hasher.hash(password),
            role=role,
            plan=plan,
            created_at=datetime.now(UTC),
        )
        return self._users.add(user)

    # --- Login ------------------------------------------------------------
    def login(self, *, email: str, password: str) -> TokenPair:
        user = self._users.get_by_email(User.normalize_email(email))
        # Mensaje genérico en todos los caminos: evita enumeración de usuarios.
        if user is None or not user.is_active:
            raise InvalidCredentials("Email o contraseña incorrectos.")
        if not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentials("Email o contraseña incorrectos.")
        return self._issue_pair(user)

    # --- Refresh (rotatorio) ---------------------------------------------
    def refresh(self, *, refresh_token: str) -> TokenPair:
        record = self._refresh.get_by_hash(hash_refresh_token(refresh_token))
        now = datetime.now(UTC)
        if record is None:
            raise InvalidToken("Refresh token inválido.")
        if record.revoked_at is not None:
            # Reuso de un token ya rotado => posible robo: revocar toda la cadena.
            self._refresh.revoke_all_for_user(record.user_id, when=now)
            raise TokenReused("Refresh token reutilizado; sesión revocada por seguridad.")
        if record.expires_at <= now:
            raise InvalidToken("Refresh token expirado.")

        user = self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise UserNotFound("El usuario ya no está disponible.")

        self._refresh.revoke(record.id, when=now)  # type: ignore[arg-type]
        return self._issue_pair(user, rotated_from=record.id)

    # --- Logout -----------------------------------------------------------
    def logout(self, *, refresh_token: str) -> None:
        record = self._refresh.get_by_hash(hash_refresh_token(refresh_token))
        if record is not None and record.revoked_at is None:
            self._refresh.revoke(record.id, when=datetime.now(UTC))  # type: ignore[arg-type]

    # --- Helpers ----------------------------------------------------------
    def _issue_pair(self, user: User, *, rotated_from: int | None = None) -> TokenPair:
        access = self._tokens.create_access_token(user)
        raw_refresh, refresh_hash = new_refresh_token()
        assert user.id is not None
        self._refresh.add(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + self._refresh_ttl,
            rotated_from=rotated_from,
        )
        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self._tokens.access_ttl_seconds,
        )
