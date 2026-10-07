"""Ingesta de selecciones nacionales: Mundial 2026 + siembra de ratings reales.

Fuentes abiertas (sin API key):
  - Fixtures/resultados del Mundial 2026: openfootball/world-cup.json (2026).
  - Historial internacional real (1872→): github.com/martj42/international_results
    (CSV). Se usa para sembrar el Elo de cada selección con datos de VERDAD.

⚠️ Honestidad: los partidos del 2026 por jugar son fixtures reales; predecirlos es
legítimo (alta incertidumbre). Los resultados ya jugados son reales. Las eliminatorias
con placeholders (1A, W73…) se omiten hasta que se definan los equipos.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from ...domain.catalog import Competition, Match, MatchStatus, Sport, Team

_WC2026_URL = "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json"
_INTL_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"

WC2026_START = "2026-06-11"  # corte para la siembra: ratings PRE-torneo

# Nombres que difieren entre el fixture 2026 y el dataset histórico.
_NATION_ALIASES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}

# Etiquetas de eliminatoria que NO son selecciones reales (aún).
_PLACEHOLDER = re.compile(r"^(\d|[WL]\d)|/")

# Elo de selecciones: K alto (pocos partidos) y ventaja de localía estándar.
_SEED_K = 30.0
_SEED_HOME_ADV = 60.0
_SEED_BASE = 1500.0


def _canonical_nation(name: str) -> str:
    return _NATION_ALIASES.get(name, name)


def _nation_code(name: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", _canonical_nation(name).upper()).strip("_")
    return f"NAT_{slug}"


def _is_real_nation(name: str | None) -> bool:
    return bool(name) and not _PLACEHOLDER.match(name)  # type: ignore[arg-type]


def _fetch(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "sports-predictor/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def _parse_kickoff(date_str: str, time_str: str | None) -> datetime:
    hour, minute = 12, 0
    if time_str:
        m = re.match(r"(\d{1,2}):(\d{2})", time_str)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
    year, month, day = (int(x) for x in date_str.split("-"))
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


@dataclass
class IngestResult:
    competition: Competition
    teams: list[Team]
    matches: list[Match]
    seed_ratings: dict[str, float]
    seed_counts: dict[str, int]


def compute_seed_ratings(
    *, cutoff: str = WC2026_START, timeout: int = 60
) -> tuple[dict[str, float], dict[str, int]]:
    """Elo de selecciones desde el historial internacional REAL anterior a ``cutoff``.

    Devuelve ``(ratings, counts)`` por código de selección. ``counts`` = número de
    partidos internacionales reales considerados (para reflejar la profundidad de
    datos en la confianza).
    """
    raw = _fetch(_INTL_URL, timeout).decode("utf-8")
    rows = [r for r in csv.DictReader(io.StringIO(raw)) if r["date"] < cutoff]
    rows.sort(key=lambda r: r["date"])

    ratings: dict[str, float] = {}
    counts: dict[str, int] = {}

    def rating(code: str) -> float:
        return ratings.get(code, _SEED_BASE)

    for r in rows:
        try:
            hs, as_ = int(r["home_score"]), int(r["away_score"])
        except (ValueError, KeyError):
            continue
        home = _nation_code(r["home_team"])
        away = _nation_code(r["away_team"])
        neutral = str(r.get("neutral", "")).strip().upper() == "TRUE"
        adv = 0.0 if neutral else _SEED_HOME_ADV
        diff = rating(home) + adv - rating(away)
        expected = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
        actual = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        delta = _SEED_K * (actual - expected)
        ratings[home] = rating(home) + delta
        ratings[away] = rating(away) - delta
        counts[home] = counts.get(home, 0) + 1
        counts[away] = counts.get(away, 0) + 1

    return {k: round(v, 1) for k, v in ratings.items()}, counts


def fetch_world_cup_2026(*, timeout: int = 60, start_match_id: int = 0) -> IngestResult:
    """Ingiere los fixtures/resultados reales del Mundial 2026 (omitiendo placeholders)."""
    import json

    data = json.loads(_fetch(_WC2026_URL, timeout).decode("utf-8"))
    competition = Competition(
        code="WC_2026",
        name="Copa del Mundo 2026",
        sport=Sport.SOCCER,
        country="Internacional",
        tier=1,
        is_mock=False,
        is_international=True,
    )

    teams: dict[str, Team] = {}
    matches: list[Match] = []
    match_id = start_match_id

    for raw in data.get("matches", []):
        t1, t2 = raw.get("team1"), raw.get("team2")
        if not (_is_real_nation(t1) and _is_real_nation(t2)):
            continue  # eliminatoria sin equipos definidos
        h_code, a_code = _nation_code(t1), _nation_code(t2)
        for code, name in ((h_code, t1), (a_code, t2)):
            teams.setdefault(
                code,
                Team(
                    code=code,
                    name=_canonical_nation(name),
                    sport=Sport.SOCCER,
                    short_name=_canonical_nation(name)[:3].upper(),
                    country=None,
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
                competition_code="WC_2026",
                season_label="2026",
                home_team=teams[h_code],
                away_team=teams[a_code],
                kickoff_utc=_parse_kickoff(raw["date"], raw.get("time")),
                status=MatchStatus.FINISHED if finished else MatchStatus.SCHEDULED,
                home_score=int(ft[0]) if finished else None,
                away_score=int(ft[1]) if finished else None,
                venue_name=None,
                stage=raw.get("round"),
                is_mock=False,
            )
        )

    seed_ratings, seed_counts = compute_seed_ratings(timeout=timeout)
    return IngestResult(competition, list(teams.values()), matches, seed_ratings, seed_counts)
