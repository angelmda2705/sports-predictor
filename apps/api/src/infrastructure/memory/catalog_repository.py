"""Repositorio de catálogo en memoria (datos mock).

Implementa el filtrado, la búsqueda y la paginación de partidos. En Fase 2 se
añade un repositorio SQLAlchemy equivalente que empuja estos filtros a SQL.
"""

from __future__ import annotations

from ...application.catalog_ports import MatchQuery
from ...domain.catalog import Competition, Match, Sport, Team
from .catalog_seed import build_mock_catalog


class InMemoryCatalogRepository:
    """Repositorio de catálogo en memoria, agnóstico a la fuente de datos.

    Funciona igual con datos mock (``from_mock``) o reales (cargados desde un
    snapshot de ingesta). Toda la lógica de filtrado/búsqueda es la misma.
    """

    def __init__(
        self,
        competitions: list[Competition],
        teams: list[Team],
        matches: list[Match],
    ) -> None:
        self._competitions = competitions
        self._teams = teams
        self._matches = sorted(matches, key=lambda m: m.kickoff_utc)
        self._team_by_code = {t.code: t for t in teams}
        self._match_by_id = {m.id: m for m in matches}

    @classmethod
    def from_mock(cls, seed: int = 42) -> InMemoryCatalogRepository:
        return cls(*build_mock_catalog(seed))

    def list_competitions(self, sport: Sport | None = None) -> list[Competition]:
        if sport is None:
            return list(self._competitions)
        return [c for c in self._competitions if c.sport == sport]

    def get_competition(self, code: str) -> Competition | None:
        return next((c for c in self._competitions if c.code == code), None)

    def list_teams(self, competition_code: str) -> list[Team]:
        comp = self.get_competition(competition_code)
        if comp is None:
            return []
        # En el mock, los equipos de una competición son los que comparten deporte y
        # participan en algún partido de esa competición.
        codes = {m.home_team.code for m in self._matches if m.competition_code == competition_code}
        codes |= {m.away_team.code for m in self._matches if m.competition_code == competition_code}
        return sorted(
            (t for t in self._teams if t.code in codes), key=lambda t: t.name
        )

    def get_team(self, code: str) -> Team | None:
        return self._team_by_code.get(code)

    def search_matches(self, query: MatchQuery) -> tuple[list[Match], int]:
        items = self._matches

        if query.sport is not None:
            items = [m for m in items if m.sport == query.sport]
        if query.competition_code is not None:
            items = [m for m in items if m.competition_code == query.competition_code]
        if query.team_code is not None:
            items = [
                m
                for m in items
                if query.team_code in (m.home_team.code, m.away_team.code)
            ]
        if query.status is not None:
            items = [m for m in items if m.status == query.status]
        if query.date_from is not None:
            items = [m for m in items if m.kickoff_utc.date() >= query.date_from]
        if query.date_to is not None:
            items = [m for m in items if m.kickoff_utc.date() <= query.date_to]
        if query.text:
            needle = query.text.casefold()
            items = [
                m
                for m in items
                if needle in m.home_team.name.casefold()
                or needle in m.away_team.name.casefold()
                or needle in m.competition_code.casefold()
            ]

        if query.order_desc:
            items = list(reversed(items))  # self._matches está ordenado asc por kickoff

        total = len(items)
        page = items[query.offset : query.offset + query.limit]
        return page, total

    def get_match(self, match_id: int) -> Match | None:
        return self._match_by_id.get(match_id)
