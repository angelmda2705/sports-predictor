"""Errores de dominio del subsistema de autenticación.

Se mapean a respuestas HTTP en la capa de interfaz. Importante para seguridad:
``InvalidCredentials`` es genérico a propósito (no revela si el email existe),
para evitar enumeración de usuarios.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base de errores de autenticación."""


class EmailAlreadyRegistered(AuthError):
    """El email ya está registrado (conflicto en alta)."""


class InvalidCredentials(AuthError):
    """Email o contraseña incorrectos (mensaje deliberadamente genérico)."""


class InvalidToken(AuthError):
    """Token inválido, expirado o revocado."""


class TokenReused(InvalidToken):
    """Se reusó un refresh token ya rotado: indicio de robo de token.

    Dispara la revocación de toda la cadena de tokens del usuario.
    """


class UserNotFound(AuthError):
    """El usuario referido por un token ya no existe o está inactivo."""
