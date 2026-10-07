"""Implementación SQLAlchemy de los puertos de repositorio.

Cada repositorio opera sobre una ``Session`` inyectada (unidad de trabajo por
request). Convierte entre modelos ORM y entidades/registros del dominio.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...application.ports import RefreshTokenRecord
from ...domain.user import Plan, Role, User
from .models import RefreshTokenModel, UserModel


def _aware(dt: datetime | None) -> datetime | None:
    """Garantiza datetimes UTC-aware al salir del adaptador.

    Postgres (``timestamptz``) ya devuelve datetimes con zona; SQLite no guarda
    tz y devuelve naive. Normalizar aquí mantiene el dominio libre de este detalle
    de persistencia y evita comparaciones naive-vs-aware.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _to_record(row: RefreshTokenModel) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        expires_at=_aware(row.expires_at),  # type: ignore[arg-type]
        revoked_at=_aware(row.revoked_at),
        rotated_from=row.rotated_from,
    )


def _to_user(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        role=Role(row.role),
        plan=Plan(row.plan),
        email_verified=row.email_verified,
        created_at=_aware(row.created_at),
        deleted_at=_aware(row.deleted_at),
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        assert user.created_at is not None
        row = UserModel(
            email=user.email,
            password_hash=user.password_hash,
            role=str(user.role),
            plan=str(user.plan),
            email_verified=user.email_verified,
            created_at=user.created_at,
            deleted_at=user.deleted_at,
        )
        self._session.add(row)
        self._session.flush()  # asigna id sin cerrar la transacción
        return _to_user(row)

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _to_user(row) if row is not None else None

    def get_by_id(self, user_id: int) -> User | None:
        row = self._session.get(UserModel, user_id)
        return _to_user(row) if row is not None else None


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        rotated_from: int | None = None,
    ) -> RefreshTokenRecord:
        row = RefreshTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            rotated_from=rotated_from,
        )
        self._session.add(row)
        self._session.flush()
        return _to_record(row)

    def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        row = self._session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        return _to_record(row) if row is not None else None

    def revoke(self, token_id: int, *, when: datetime) -> None:
        row = self._session.get(RefreshTokenModel, token_id)
        if row is not None and row.revoked_at is None:
            row.revoked_at = when
            self._session.flush()

    def revoke_all_for_user(self, user_id: int, *, when: datetime) -> None:
        rows = self._session.scalars(
            select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        for row in rows:
            row.revoked_at = when
        self._session.flush()
