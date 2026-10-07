"""Endpoints de catálogo: competiciones, equipos y partidos.

Lectura pública (sin auth) en el MVP. Los límites por plan de suscripción se
aplican en un incremento posterior.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...application.catalog_ports import MatchQuery
from ...application.catalog_service import CatalogService
from ...domain.catalog import MatchStatus, Sport
from ..deps import get_catalog_service
from ..schemas_catalog import (
    CompetitionResponse,
    MatchListResponse,
    MatchResponse,
    TeamResponse,
)

router = APIRouter(tags=["catalog"])


@router.get("/competitions", response_model=list[CompetitionResponse])
def list_competitions(
    sport: Sport | None = Query(default=None),
    service: CatalogService = Depends(get_catalog_service),
) -> list[CompetitionResponse]:
    return [CompetitionResponse.from_domain(c) for c in service.list_competitions(sport)]


@router.get("/competitions/{code}", response_model=CompetitionResponse)
def get_competition(
    code: str, service: CatalogService = Depends(get_catalog_service)
) -> CompetitionResponse:
    comp = service.get_competition(code)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Competición no encontrada.")
    return CompetitionResponse.from_domain(comp)


@router.get("/competitions/{code}/teams", response_model=list[TeamResponse])
def list_teams(
    code: str, service: CatalogService = Depends(get_catalog_service)
) -> list[TeamResponse]:
    if service.get_competition(code) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Competición no encontrada.")
    return [TeamResponse.from_domain(t) for t in service.list_teams(code)]


@router.get("/teams/{code}", response_model=TeamResponse)
def get_team(code: str, service: CatalogService = Depends(get_catalog_service)) -> TeamResponse:
    team = service.get_team(code)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado.")
    return TeamResponse.from_domain(team)


@router.get("/matches", response_model=MatchListResponse)
def list_matches(
    sport: Sport | None = Query(default=None),
    competition: str | None = Query(default=None),
    team: str | None = Query(default=None),
    match_status: MatchStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None, description="Búsqueda por nombre de equipo"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: CatalogService = Depends(get_catalog_service),
) -> MatchListResponse:
    items, total = service.search_matches(
        MatchQuery(
            sport=sport,
            competition_code=competition,
            team_code=team,
            status=match_status,
            date_from=date_from,
            date_to=date_to,
            text=q,
            order_desc=(order == "desc"),
            limit=limit,
            offset=offset,
        )
    )
    responses = [MatchResponse.from_domain(m) for m in items]
    return MatchListResponse(
        items=responses,
        total=total,
        limit=limit,
        offset=offset,
        contains_mock=any(m.is_mock for m in responses),
    )


@router.get("/matches/{match_id}", response_model=MatchResponse)
def get_match(
    match_id: int, service: CatalogService = Depends(get_catalog_service)
) -> MatchResponse:
    match = service.get_match(match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Partido no encontrado.")
    return MatchResponse.from_domain(match)
