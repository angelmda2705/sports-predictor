"""Puerto del repositorio de catálogo y especificación de consulta de partidos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ..domain.catalog import Competition, Match, MatchStatus, Sport, Team


@dataclass(frozen=True)
class MatchQuery:
    """Filtros para listar partidos. Todos opcionales (combinables)."""

    sport: Sport | None = None
    competition_code: str | None = None
    team_code: str | None = None
    status: MatchStatus | None = None
    date_from: date | None = None  # inclusivo (por fecha de kickoff, UTC)
    date_to: date | None = None  # inclusivo
    text: str | None = None  # búsqueda por nombre de equipo/competición
    order_desc: bool = False  # True = más recientes primero (por kickoff)
    limit: int = 50
    offset: int = 0


class CatalogRepository(Protocol):
    def list_competitions(self, sport: Sport | None = None) -> list[Competition]: ...

    def get_competition(self, code: str) -> Competition | None: ...

    def list_teams(self, competition_code: str) -> list[Team]: ...

    def get_team(self, code: str) -> Team | None: ...

    def search_matches(self, query: MatchQuery) -> tuple[list[Match], int]:
        """Devuelve ``(pagina_de_partidos, total_sin_paginar)``."""
        ...

    def get_match(self, match_id: int) -> Match | None: ...
