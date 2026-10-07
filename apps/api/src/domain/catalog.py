"""Entidades del catálogo deportivo: deporte, competición, equipo y partido."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Sport(StrEnum):
    SOCCER = "soccer"
    AMERICAN_FOOTBALL = "american_football"


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


@dataclass(frozen=True)
class Competition:
    code: str  # código canónico, ej. 'ENG_PL', 'NFL'
    name: str
    sport: Sport
    country: str | None = None
    tier: int | None = None
    is_mock: bool = False
    # Torneo de selecciones nacionales (Mundial). Indica que los ratings se
    # siembran con historial internacional, no con la propia competición.
    is_international: bool = False


@dataclass(frozen=True)
class Team:
    code: str  # código canónico, ej. 'ENG_ARS'
    name: str
    sport: Sport
    short_name: str | None = None
    country: str | None = None
    is_mock: bool = False


@dataclass(frozen=True)
class Match:
    id: int
    sport: Sport
    competition_code: str
    season_label: str
    home_team: Team
    away_team: Team
    kickoff_utc: datetime
    status: MatchStatus
    home_score: int | None = None
    away_score: int | None = None
    venue_name: str | None = None
    # Fase del torneo (ej. "Fase de grupos · Grupo A", "Octavos"). Útil para
    # competiciones por eliminatoria como la Copa del Mundo. None en ligas.
    stage: str | None = None
    is_mock: bool = False
