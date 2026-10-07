"""Schemas Pydantic de entrada/salida. Validación estricta de entradas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from ..domain.user import Plan, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    # Mínimo 8 caracteres; tope alto para no romper Argon2 ni habilitar DoS por hash.
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos de vida del access token


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: Role
    plan: Plan
    email_verified: bool
