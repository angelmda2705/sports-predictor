"""Schemas de estado de proveedores de datos."""

from __future__ import annotations

from pydantic import BaseModel


class AccountInfo(BaseModel):
    name: str | None
    email: str | None
    plan: str | None
    active: bool
    requests_today: int | None
    daily_limit: int | None


class ProviderStatus(BaseModel):
    name: str
    configured: bool  # ¿hay API key puesta?
    connected: bool  # ¿la llamada en vivo funcionó?
    account: AccountInfo | None
    error: str | None
    note: str


class ProvidersStatusResponse(BaseModel):
    providers: list[ProviderStatus]
