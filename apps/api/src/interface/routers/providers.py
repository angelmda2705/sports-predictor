"""Estado de los proveedores de datos (incluido el de pago, API-Football)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ...infrastructure.providers.api_football import ApiFootballClient, ApiFootballError
from ..schemas_providers import AccountInfo, ProviderStatus, ProvidersStatusResponse

router = APIRouter(tags=["providers"])


@router.get("/providers/status", response_model=ProvidersStatusResponse)
def providers_status(request: Request) -> ProvidersStatusResponse:
    settings = request.app.state.settings
    client: ApiFootballClient | None = request.app.state.api_football_client

    configured = settings.api_football_configured
    connected = False
    account: AccountInfo | None = None
    error: str | None = None

    if client is not None:
        # Llamada real a API-Football para verificar la key (sin exponerla).
        try:
            acc = client.account_status()
            connected = True
            account = AccountInfo(
                name=acc.name,
                email=acc.email,
                plan=acc.plan,
                active=acc.active,
                requests_today=acc.requests_today,
                daily_limit=acc.daily_limit,
            )
        except ApiFootballError as exc:
            error = str(exc)

    note = (
        "Conectado." if connected
        else "Pon tu API key en .env (API_FOOTBALL_KEY) y reinicia para activar." if not configured
        else "Key configurada pero la verificación falló (revisa la key o el plan)."
    )
    return ProvidersStatusResponse(
        providers=[
            ProviderStatus(
                name="api-football",
                configured=configured,
                connected=connected,
                account=account,
                error=error,
                note=note,
            )
        ]
    )
