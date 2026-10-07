"""Hashing de contraseñas con Argon2id.

Argon2id es el esquema recomendado actualmente para contraseñas (ganador del
Password Hashing Competition). Nunca se almacena la contraseña en claro.
"""

from __future__ import annotations

from typing import Protocol

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class Argon2PasswordHasher:
    """Implementación de ``PasswordHasher`` basada en argon2-cffi (Argon2id)."""

    def __init__(self) -> None:
        self._hasher = _Argon2Hasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
