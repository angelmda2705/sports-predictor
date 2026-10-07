"""Schemas de respuesta del catálogo."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..domain.catalog import Competition, Match, MatchStatus, Sport, Team


class CompetitionResponse(BaseModel):
    code: str
    name: str
    sport: Sport
    country: str | None
    tier: int | None
    is_mock: bool

    @classmethod
    def from_domain(cls, c: Competition) -> CompetitionResponse:
        return cls(
            code=c.code, name=c.name, sport=c.sport, country=c.country, tier=c.tier,
            is_mock=c.is_mock,
        )


class TeamResponse(BaseModel):
    code: str
    name: str
    short_name: str | None
    sport: Sport
    country: str | None
    is_mock: bool

    @classmethod
    def from_domain(cls, t: Team) -> TeamResponse:
        return cls(
            code=t.code, name=t.name, short_name=t.short_name, sport=t.sport,
            country=t.country, is_mock=t.is_mock,
        )


class TeamRef(BaseModel):
    code: str
    name: str
    short_name: str | None


class MatchResponse(BaseModel):
    id: int
    sport: Sport
    competition_code: str
    season_label: str
    home_team: TeamRef
    away_team: TeamRef
    kickoff_utc: datetime
    status: MatchStatus
    home_score: int | None
    away_score: int | None
    venue_name: str | None
    stage: str | None
    is_mock: bool

    @classmethod
    def from_domain(cls, m: Match) -> MatchResponse:
        return cls(
            id=m.id,
            sport=m.sport,
            competition_code=m.competition_code,
            season_label=m.season_label,
            home_team=TeamRef(
                code=m.home_team.code, name=m.home_team.name, short_name=m.home_team.short_name
            ),
            away_team=TeamRef(
                code=m.away_team.code, name=m.away_team.name, short_name=m.away_team.short_name
            ),
            kickoff_utc=m.kickoff_utc,
            status=m.status,
            home_score=m.home_score,
            away_score=m.away_score,
            venue_name=m.venue_name,
            stage=m.stage,
            is_mock=m.is_mock,
        )


class MatchListResponse(BaseModel):
    items: list[MatchResponse]
    total: int
    limit: int
    offset: int
    # Bandera para que la UI muestre el banner de datos de prueba.
    contains_mock: bool
