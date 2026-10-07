"""Predicción individual de jugadores con datos reales (proveedor de pago).

Requiere `API_FOOTBALL_KEY` en .env. Si no hay key, responde 503 con instrucción
clara (no inventa datos). Honestidad: el modelo es un baseline per-90 ponderado por
recencia; toda salida es probabilística, no una certeza.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from ...application.player_service import (
    PlayerNotFound,
    PlayerPredictionResult,
    PlayerService,
)
from ...infrastructure.providers.api_football import ApiFootballError
from ..schemas_players import (
    PlayerGameRowOut,
    PlayerPredictionOut,
    PlayerPredictionResponse,
)

router = APIRouter(tags=["players"])

_DISCLAIMER = (
    "Predicción probabilística (no es una certeza). Baseline per-90 ponderado por "
    "recencia: primero estima titularidad y minutos, luego escala las estadísticas. "
    "Con pocos partidos la confianza baja. Datos reales de API-Football."
)


def _to_response(result: PlayerPredictionResult) -> PlayerPredictionResponse:
    p = result.prediction
    return PlayerPredictionResponse(
        player=result.player,
        team=result.team,
        season=result.season,
        n_fixtures_scanned=result.n_fixtures_scanned,
        games=[
            PlayerGameRowOut(
                date=g.date,
                opponent=g.opponent,
                started=g.started,
                minutes=g.minutes,
                goals=g.goals,
                assists=g.assists,
                shots=g.shots,
            )
            for g in result.games
        ],
        prediction=PlayerPredictionOut(
            n_games=p.n_games,
            prob_start=p.prob_start,
            expected_minutes=p.expected_minutes,
            expected_goals=p.expected_goals,
            expected_assists=p.expected_assists,
            expected_shots=p.expected_shots,
            expected_shots_on=p.expected_shots_on,
            prob_scores=p.prob_scores,
            confidence=p.confidence,
            confidence_band=p.confidence_band,
            low_confidence_note=p.low_confidence_note,
            factors=p.factors,
        ),
        disclaimer=_DISCLAIMER,
    )


@router.get("/players/predict", response_model=PlayerPredictionResponse)
def players_predict(
    request: Request,
    name: str = Query(..., min_length=2, description="Nombre (o apellido) del jugador."),
    team: str = Query(..., min_length=2, description="Equipo/selección, p. ej. 'Mexico'."),
    season: int = Query(2022, description="Temporada. Free: 2022-2024. Pro desbloquea 2026."),
    league: int | None = Query(None, description="Liga opcional (p. ej. 1 = Copa del Mundo)."),
) -> PlayerPredictionResponse:
    service: PlayerService | None = request.app.state.player_service
    if service is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proveedor de pago no configurado. Pon API_FOOTBALL_KEY en .env y reinicia.",
        )
    try:
        result = service.predict(name, team, season=season, league=league)
    except PlayerNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApiFootballError as exc:
        # Errores del proveedor (p. ej. temporada bloqueada en Free) → 502 explícito.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Proveedor: {exc}") from exc
    return _to_response(result)
