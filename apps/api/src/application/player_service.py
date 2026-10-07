"""Servicio de predicción individual de jugadores con datos REALES de API-Football.

Construye el historial reciente de un jugador (per-partido) desde el proveedor de
pago y lo pasa al baseline ML (`predict_player`). Es **agnóstico a la temporada**:
en el plan Free se usan 2022-2024 (validación con el Mundial 2022); con Pro se usa
2026 (Mundial en vivo). El MISMO código sirve para ambos — solo cambia `season`.

Cuota: cada predicción gasta 1 (buscar equipo) + 1 (fixtures) + F llamadas a
`/fixtures/players` (una por partido terminado). Para una selección en un Mundial,
F es pequeño (3-7 partidos).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sports_predictor_ml.players.baseline import (
    PlayerGameLog,
    PlayerPrediction,
    predict_player,
)

from ..infrastructure.providers.api_football import (
    ApiFootballClient,
    FixtureRef,
    PlayerMatchStats,
)

# Estados de partido TERMINADO en API-Football (con resultado útil para el historial).
_FINISHED = {"FT", "AET", "PEN"}


class PlayerNotFound(Exception):
    """No se encontró el equipo o el jugador en los partidos de esa temporada."""


@dataclass(frozen=True)
class PlayerGameRow:
    """Una fila del historial mostrado al usuario (transparencia: de dónde sale)."""

    date: str
    opponent: str
    started: bool
    minutes: int
    goals: int
    assists: int
    shots: int


@dataclass(frozen=True)
class PlayerPredictionResult:
    player: str
    team: str
    season: int
    n_fixtures_scanned: int
    games: list[PlayerGameRow]
    prediction: PlayerPrediction


def _parse_dt(iso: str) -> datetime:
    # API-Football entrega ISO8601 con zona, p. ej. "2022-11-22T16:00:00+00:00".
    return datetime.fromisoformat(iso)


def _opponent(fx: FixtureRef, team: str) -> str:
    if team.lower() == fx.home.lower():
        return fx.away
    if team.lower() == fx.away.lower():
        return fx.home
    return fx.away  # respaldo si el nombre no calza exacto


def _to_log(stats: PlayerMatchStats, kickoff: datetime) -> PlayerGameLog:
    """Convierte stats por partido del proveedor al log que consume el modelo ML."""
    return PlayerGameLog(
        kickoff=kickoff,
        started=stats.started,
        minutes=stats.minutes or 0,  # suplente sin jugar → 0 minutos
        goals=stats.goals,
        assists=stats.assists,
        shots=stats.shots,
        shots_on=stats.shots_on,
        key_passes=stats.key_passes,
    )


def _to_row(stats: PlayerMatchStats, fx: FixtureRef) -> PlayerGameRow:
    return PlayerGameRow(
        date=fx.kickoff[:10],
        opponent=_opponent(fx, stats.team),
        started=stats.started,
        minutes=stats.minutes or 0,
        goals=stats.goals,
        assists=stats.assists,
        shots=stats.shots,
    )


class PlayerService:
    def __init__(self, client: ApiFootballClient) -> None:
        self._client = client

    def predict(
        self,
        player_name: str,
        team_name: str,
        *,
        season: int,
        league: int | None = None,
    ) -> PlayerPredictionResult:
        team_id = self._client.find_team_id(team_name, national=True)
        if team_id is None:
            team_id = self._client.find_team_id(team_name)
        if team_id is None:
            raise PlayerNotFound(f"No encontré el equipo '{team_name}'.")

        fixtures = self._client.team_fixtures(team_id, season, league=league)
        finished = [f for f in fixtures if f.status in _FINISHED]

        # Por substring puede coincidir más de un jugador (p. ej. "Sanchez");
        # agrupamos por nombre EXACTO y nos quedamos con el de más apariciones.
        matched: dict[str, list[tuple[PlayerMatchStats, FixtureRef]]] = {}
        for fx in finished:
            for ps in self._client.fixture_player_stats(fx.fixture_id):
                if player_name.lower() in ps.player.lower():
                    matched.setdefault(ps.player, []).append((ps, fx))

        if not matched:
            raise PlayerNotFound(
                f"No encontré a '{player_name}' en los partidos de {team_name} en {season}."
            )

        best_name = max(matched, key=lambda k: len(matched[k]))
        pairs = sorted(matched[best_name], key=lambda p: p[1].kickoff)

        logs = [_to_log(ps, _parse_dt(fx.kickoff)) for ps, fx in pairs]
        rows = [_to_row(ps, fx) for ps, fx in pairs]
        team_actual = pairs[0][0].team

        return PlayerPredictionResult(
            player=best_name,
            team=team_actual,
            season=season,
            n_fixtures_scanned=len(finished),
            games=rows,
            prediction=predict_player(logs),
        )
