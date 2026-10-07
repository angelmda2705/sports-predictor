"""Repositorios en memoria. Deterministas y sin dependencias externas.

Se usan en pruebas y como modo de demo local sin Postgres. NO son para producción
(no persisten entre reinicios ni son thread-safe para alta concurrencia).
"""

from __future__ import annotations

import copy
from datetime import datetime

from ...application.ports import RefreshTokenRecord
from ...domain.user import User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, User] = {}
        self._email_index: dict[str, int] = {}
        self._seq = 0

    def add(self, user: User) -> User:
        self._seq += 1
        stored = copy.deepcopy(user)
        stored.id = self._seq
        self._by_id[stored.id] = stored
        self._email_index[stored.email] = stored.id
        return copy.deepcopy(stored)

    def get_by_email(self, email: str) -> User | None:
        user_id = self._email_index.get(email)
        return copy.deepcopy(self._by_id[user_id]) if user_id is not None else None

    def get_by_id(self, user_id: int) -> User | None:
        user = self._by_id.get(user_id)
        return copy.deepcopy(user) if user is not None else None


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, RefreshTokenRecord] = {}
        self._hash_index: dict[str, int] = {}
        self._seq = 0

    def add(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        rotated_from: int | None = None,
    ) -> RefreshTokenRecord:
        self._seq += 1
        record = RefreshTokenRecord(
            id=self._seq,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            rotated_from=rotated_from,
        )
        self._by_id[record.id] = record
        self._hash_index[token_hash] = record.id
        return copy.deepcopy(record)

    def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        token_id = self._hash_index.get(token_hash)
        return copy.deepcopy(self._by_id[token_id]) if token_id is not None else None

    def revoke(self, token_id: int, *, when: datetime) -> None:
        record = self._by_id.get(token_id)
        if record is not None and record.revoked_at is None:
            record.revoked_at = when

    def revoke_all_for_user(self, user_id: int, *, when: datetime) -> None:
        for record in self._by_id.values():
            if record.user_id == user_id and record.revoked_at is None:
                record.revoked_at = when
