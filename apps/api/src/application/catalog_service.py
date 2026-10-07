"""Servicio de lectura del catálogo.

Capa delgada sobre el repositorio: aplica límites de paginación seguros y delega
las consultas. No corre modelos ni escribe datos.
"""

from __future__ import annotations

from dataclasses import replace

from ..domain.catalog import Competition, Match, Team
from .catalog_ports import CatalogRepository, MatchQuery

MAX_PAGE_SIZE = 100


class CatalogService:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def list_competitions(self, sport=None) -> list[Competition]:
        return self._repo.list_competitions(sport)

    def get_competition(self, code: str) -> Competition | None:
        return self._repo.get_competition(code)

    def list_teams(self, competition_code: str) -> list[Team]:
        return self._repo.list_teams(competition_code)

    def get_team(self, code: str) -> Team | None:
        return self._repo.get_team(code)

    def search_matches(self, query: MatchQuery) -> tuple[list[Match], int]:
        safe = replace(
            query,
            limit=max(1, min(query.limit, MAX_PAGE_SIZE)),
            offset=max(0, query.offset),
        )
        return self._repo.search_matches(safe)

    def get_match(self, match_id: int) -> Match | None:
        return self._repo.get_match(match_id)
