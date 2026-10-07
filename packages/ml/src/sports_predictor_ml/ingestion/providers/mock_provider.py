"""Proveedor MOCK para desarrollo (Fase 1).

Genera datos deterministas de la Premier League **claramente etiquetados** con
``is_mock=True``. Sirve para construir y probar el pipeline, la API y la UI sin
depender de un proveedor real ni de su licenciamiento.

⚠️ Estos datos NO son reales. No representan equipos, resultados ni lesiones
verídicas. Existen únicamente para desarrollo y pruebas, y la UI debe mostrar un
banner cuando una vista contenga datos con ``is_mock=True``.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from .base import (
    InjuryDTO,
    MatchDTO,
    ProviderMetadata,
    TeamDTO,
)

# Subconjunto de equipos de la Premier League usados como semilla de desarrollo.
_PL_TEAMS: tuple[tuple[str, str, str], ...] = (
    ("ARS", "Arsenal", "ARS"),
    ("CHE", "Chelsea", "CHE"),
    ("LIV", "Liverpool", "LIV"),
    ("MCI", "Manchester City", "MCI"),
    ("MUN", "Manchester United", "MUN"),
    ("TOT", "Tottenham Hotspur", "TOT"),
    ("NEW", "Newcastle United", "NEW"),
    ("AVL", "Aston Villa", "AVL"),
)


class MockSportsDataProvider:
    """Implementación en memoria del puerto ``SportsDataProvider``.

    Determinista: con la misma ``seed`` produce siempre los mismos datos, lo que
    facilita pruebas reproducibles.
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="mock",
            requires_api_key=False,
            is_mock=True,
            supported_sports=("soccer",),
        )

    def fetch_teams(self, competition_ref: str, season_label: str) -> list[TeamDTO]:
        return [
            TeamDTO(
                provider_ref=ref,
                name=name,
                short_name=short,
                country="England",
                is_mock=True,
            )
            for ref, name, short in _PL_TEAMS
        ]

    def fetch_matches(self, competition_ref: str, season_label: str) -> list[MatchDTO]:
        """Genera un mini round-robin determinista.

        Los partidos cuyo kickoff es anterior a ``base`` se marcan como
        ``finished`` con marcador; el resto quedan ``scheduled`` sin marcador,
        para ejercitar tanto el histórico como los próximos partidos.
        """
        rng = random.Random(self._seed)
        teams = [t[0] for t in _PL_TEAMS]
        base = datetime(2025, 8, 16, 14, 0, tzinfo=UTC)
        matches: list[MatchDTO] = []
        match_index = 0
        for i, home in enumerate(teams):
            for away in teams[i + 1 :]:
                kickoff = base + timedelta(days=7 * match_index)
                # Mitad del calendario "ya jugada", mitad "por jugar".
                is_finished = match_index < (len(teams) * (len(teams) - 1) // 2) // 2
                home_score = rng.randint(0, 4) if is_finished else None
                away_score = rng.randint(0, 4) if is_finished else None
                matches.append(
                    MatchDTO(
                        provider_ref=f"mock-{match_index:04d}",
                        competition_ref=competition_ref,
                        season_label=season_label,
                        home_team_ref=home,
                        away_team_ref=away,
                        kickoff_utc=kickoff,
                        status="finished" if is_finished else "scheduled",
                        home_score=home_score,
                        away_score=away_score,
                        venue_name=f"{home} Stadium (mock)",
                        is_mock=True,
                    )
                )
                match_index += 1
        return matches

    def fetch_injuries(self, competition_ref: str, season_label: str) -> list[InjuryDTO]:
        return [
            InjuryDTO(
                player_ref="mock-player-001",
                team_ref="ARS",
                status="questionable",
                reported_at=datetime(2025, 8, 14, 9, 0, tzinfo=UTC),
                source="mock",
                is_mock=True,
            )
        ]
