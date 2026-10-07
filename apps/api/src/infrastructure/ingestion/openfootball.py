"""Adaptador de datos REALES: openfootball / football.json.

Fuente: https://github.com/openfootball  (datos abiertos, dominio público, sin API key).
Formato por archivo: {"name": "...", "matches": [{round, date, time, team1, team2,
score:{ft:[h,a], ht:[h,a]}}]}.

Convierte los resultados reales a las entidades del catálogo. NO marca is_mock
(estos datos son reales). Solo stdlib (urllib): sin dependencias nuevas.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from ...domain.catalog import Competition, Match, MatchStatus, Sport, Team

_RAW = "https://raw.githubusercontent.com/openfootball"


@dataclass(frozen=True)
class DatasetSpec:
    competition_code: str
    competition_name: str
    country: str | None
    season_label: str
    url: str
    is_international: bool = False


# Datasets reales de clubes por defecto: Premier League (3 temporadas).
# El Mundial 2026 y la siembra de selecciones se ingieren aparte (ver international.py).
DEFAULT_DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec("ENG_PL", "Premier League", "England", "2021-22",
                f"{_RAW}/football.json/master/2021-22/en.1.json"),
    DatasetSpec("ENG_PL", "Premier League", "England", "2022-23",
                f"{_RAW}/football.json/master/2022-23/en.1.json"),
    DatasetSpec("ENG_PL", "Premier League", "England", "2023-24",
                f"{_RAW}/football.json/master/2023-24/en.1.json"),
)

_SUFFIX = re.compile(r"\b(FC|AFC|CF|SC)\b", re.IGNORECASE)


def _slug(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def _short_name(name: str) -> str:
    clean = _SUFFIX.sub("", name).strip()
    letters = re.sub(r"[^A-Za-z]", "", clean)
    return (letters[:3].upper() if letters else name[:3].upper())


def _team_code(spec: DatasetSpec, name: str) -> str:
    prefix = "NAT" if spec.is_international else "ENG"
    return f"{prefix}_{_slug(name)}"


def _parse_kickoff(date_str: str | None, time_str: str | None) -> datetime:
    hour, minute = 12, 0
    if time_str:
        try:
            hour, minute = (int(x) for x in time_str.split(":")[:2])
        except ValueError:
            pass
    year, month, day = (int(x) for x in (date_str or "1970-01-01").split("-"))
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _fetch_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "sports-predictor/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL controlada)
        return json.loads(resp.read().decode("utf-8"))


def fetch_real_catalog(
    datasets: tuple[DatasetSpec, ...] = DEFAULT_DATASETS, *, timeout: int = 30
) -> tuple[list[Competition], list[Team], list[Match]]:
    """Descarga y normaliza los datasets reales al modelo de catálogo.

    Los datasets que fallen (p. ej. una temporada que no existe) se omiten para
    no abortar toda la ingesta.
    """
    competitions: dict[str, Competition] = {}
    teams: dict[str, Team] = {}
    matches: list[Match] = []
    match_id = 0

    for spec in datasets:
        try:
            data = _fetch_json(spec.url, timeout)
        except Exception:  # noqa: BLE001 — dataset opcional; se omite si falla
            continue

        competitions.setdefault(
            spec.competition_code,
            Competition(
                code=spec.competition_code,
                name=spec.competition_name,
                sport=Sport.SOCCER,
                country=spec.country,
                tier=1,
                is_mock=False,
            ),
        )

        for raw in data.get("matches", []):
            home_name = raw.get("team1")
            away_name = raw.get("team2")
            if not home_name or not away_name:
                continue
            home_code = _team_code(spec, home_name)
            away_code = _team_code(spec, away_name)
            for code, name in ((home_code, home_name), (away_code, away_name)):
                teams.setdefault(
                    code,
                    Team(
                        code=code,
                        name=name,
                        sport=Sport.SOCCER,
                        short_name=_short_name(name),
                        country=None if spec.is_international else spec.country,
                        is_mock=False,
                    ),
                )

            score = raw.get("score") or {}
            ft = score.get("ft")
            finished = isinstance(ft, list) and len(ft) == 2

            match_id += 1
            matches.append(
                Match(
                    id=match_id,
                    sport=Sport.SOCCER,
                    competition_code=spec.competition_code,
                    season_label=spec.season_label,
                    home_team=teams[home_code],
                    away_team=teams[away_code],
                    kickoff_utc=_parse_kickoff(raw.get("date"), raw.get("time")),
                    status=MatchStatus.FINISHED if finished else MatchStatus.SCHEDULED,
                    home_score=int(ft[0]) if finished else None,
                    away_score=int(ft[1]) if finished else None,
                    venue_name=None,
                    stage=raw.get("round"),
                    is_mock=False,
                )
            )

    return list(competitions.values()), list(teams.values()), matches
