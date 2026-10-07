"""Construye un catálogo MOCK determinista (Premier League + NFL reducidos).

⚠️ DATOS DE PRUEBA. Todo lleva is_mock=True. No representan equipos, calendarios ni
resultados reales. En Fase 2 el catálogo se poblará desde el pipeline de ingesta a
partir de proveedores autorizados; este seed solo sirve para desarrollo y demo.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from ...domain.catalog import Competition, Match, MatchStatus, Sport, Team

_PL_TEAMS = [
    ("ENG_ARS", "Arsenal", "ARS"),
    ("ENG_CHE", "Chelsea", "CHE"),
    ("ENG_LIV", "Liverpool", "LIV"),
    ("ENG_MCI", "Manchester City", "MCI"),
    ("ENG_MUN", "Manchester United", "MUN"),
    ("ENG_TOT", "Tottenham Hotspur", "TOT"),
    ("ENG_NEW", "Newcastle United", "NEW"),
    ("ENG_AVL", "Aston Villa", "AVL"),
]

_NFL_TEAMS = [
    ("NFL_KC", "Kansas City Chiefs", "KC"),
    ("NFL_BUF", "Buffalo Bills", "BUF"),
    ("NFL_SF", "San Francisco 49ers", "SF"),
    ("NFL_DAL", "Dallas Cowboys", "DAL"),
]

# Copa del Mundo (mock). Selecciones nacionales. ⚠️ Grupos y calendario son
# ILUSTRATIVOS, NO el sorteo ni el fixture oficial. Solo para demo.
_WC_GROUPS: dict[str, list[tuple[str, str, str, str]]] = {
    "Grupo A": [
        ("WC_MEX", "México", "MEX", "Mexico"),
        ("WC_BRA", "Brasil", "BRA", "Brazil"),
        ("WC_ARG", "Argentina", "ARG", "Argentina"),
        ("WC_FRA", "Francia", "FRA", "France"),
    ],
    "Grupo B": [
        ("WC_ESP", "España", "ESP", "Spain"),
        ("WC_ENG", "Inglaterra", "ENG", "England"),
        ("WC_GER", "Alemania", "GER", "Germany"),
        ("WC_POR", "Portugal", "POR", "Portugal"),
    ],
}

_WC_VENUES = [
    "Estadio Azteca (mock)",
    "MetLife Stadium (mock)",
    "BC Place (mock)",
    "Estadio Akron (mock)",
]


def build_mock_catalog(
    seed: int = 42,
) -> tuple[list[Competition], list[Team], list[Match]]:
    rng = random.Random(seed)

    competitions = [
        Competition("ENG_PL", "Premier League (mock)", Sport.SOCCER, "England", 1, is_mock=True),
        Competition("NFL", "NFL (mock)", Sport.AMERICAN_FOOTBALL, "USA", 1, is_mock=True),
        Competition(
            "WC_2026",
            "Copa del Mundo 2026 (mock)",
            Sport.SOCCER,
            "Internacional",
            1,
            is_mock=True,
            is_international=True,
        ),
    ]

    teams: list[Team] = []
    teams += [Team(c, n, Sport.SOCCER, s, "England", is_mock=True) for c, n, s in _PL_TEAMS]
    teams += [Team(c, n, Sport.AMERICAN_FOOTBALL, s, "USA", is_mock=True) for c, n, s in _NFL_TEAMS]
    teams += [
        Team(code, name, Sport.SOCCER, short, country, is_mock=True)
        for group in _WC_GROUPS.values()
        for code, name, short, country in group
    ]
    by_code = {t.code: t for t in teams}

    matches: list[Match] = []
    match_id = 0

    def _add_round_robin(
        sport: Sport,
        competition_code: str,
        team_codes: list[str],
        finished_before: datetime,
        scheduled_start: datetime,
    ) -> None:
        nonlocal match_id
        pairs = [
            (h, a)
            for i, h in enumerate(team_codes)
            for a in team_codes[i + 1 :]
        ]
        half = len(pairs) // 2
        for idx, (home, away) in enumerate(pairs):
            match_id += 1
            is_finished = idx < half
            if is_finished:
                kickoff = finished_before - timedelta(days=7 * (half - idx))
                home_score = rng.randint(0, 4)
                away_score = rng.randint(0, 4)
                status = MatchStatus.FINISHED
            else:
                kickoff = scheduled_start + timedelta(days=7 * (idx - half))
                home_score = None
                away_score = None
                status = MatchStatus.SCHEDULED
            matches.append(
                Match(
                    id=match_id,
                    sport=sport,
                    competition_code=competition_code,
                    season_label="2025-2026",
                    home_team=by_code[home],
                    away_team=by_code[away],
                    kickoff_utc=kickoff,
                    status=status,
                    home_score=home_score,
                    away_score=away_score,
                    venue_name=f"{by_code[home].short_name} Stadium (mock)",
                    is_mock=True,
                )
            )

    _add_round_robin(
        Sport.SOCCER,
        "ENG_PL",
        [c for c, _, _ in _PL_TEAMS],
        finished_before=datetime(2026, 5, 24, 14, 0, tzinfo=UTC),
        scheduled_start=datetime(2026, 7, 4, 14, 0, tzinfo=UTC),
    )
    _add_round_robin(
        Sport.AMERICAN_FOOTBALL,
        "NFL",
        [c for c, _, _ in _NFL_TEAMS],
        finished_before=datetime(2026, 1, 5, 18, 0, tzinfo=UTC),
        scheduled_start=datetime(2026, 9, 6, 18, 0, tzinfo=UTC),
    )

    # Copa del Mundo 2026 (mock): fase de grupos en 3 jornadas (round-robin de 4).
    # J1 y J2 quedan FINISHED (antes del "hoy" del proyecto, 2026-06-24); J3 queda
    # SCHEDULED. Así cada selección llega a su próximo partido con 2 resultados
    # previos, y las predicciones del modelo tienen historial real con que trabajar.
    today = datetime(2026, 6, 24, tzinfo=UTC)
    # Emparejamientos por jornada (índices del grupo): cada par una sola vez.
    wc_rounds = [
        [(0, 1), (2, 3)],  # J1
        [(0, 2), (3, 1)],  # J2
        [(0, 3), (1, 2)],  # J3 (por jugar)
    ]
    group_base = {
        "Grupo A": datetime(2026, 6, 18, 18, 0, tzinfo=UTC),
        "Grupo B": datetime(2026, 6, 19, 18, 0, tzinfo=UTC),
    }
    matchday_offset_days = [0, 3, 7]
    venue_idx = 0
    for group_name, group_teams in _WC_GROUPS.items():
        codes = [c for c, _, _, _ in group_teams]
        base = group_base[group_name]
        for md, pairs in enumerate(wc_rounds):
            kickoff = base + timedelta(days=matchday_offset_days[md])
            is_finished = kickoff < today
            for hi, ai in pairs:
                match_id += 1
                matches.append(
                    Match(
                        id=match_id,
                        sport=Sport.SOCCER,
                        competition_code="WC_2026",
                        season_label="2026",
                        home_team=by_code[codes[hi]],
                        away_team=by_code[codes[ai]],
                        kickoff_utc=kickoff,
                        status=MatchStatus.FINISHED if is_finished else MatchStatus.SCHEDULED,
                        home_score=rng.randint(0, 3) if is_finished else None,
                        away_score=rng.randint(0, 3) if is_finished else None,
                        venue_name=_WC_VENUES[venue_idx % len(_WC_VENUES)],
                        stage=f"Fase de grupos · {group_name} · J{md + 1}",
                        is_mock=True,
                    )
                )
                venue_idx += 1

    return competitions, teams, matches
