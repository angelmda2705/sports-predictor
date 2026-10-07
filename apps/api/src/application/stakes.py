"""Análisis de "lo que está en juego" (stakes) para torneos de grupos.

Reconstruye los grupos y, para un partido próximo, determina contextos de bajo
incentivo (que el modelo no puede ver, porque no conoce alineaciones):

- **Clasificación asegurada**: el equipo ya garantizó el top-2 de su grupo.
- **Eliminado**: el equipo ya no puede clasificar (ni top-2 ni mejor tercero).

Ambas detecciones son CONSERVADORAS y SÓLIDAS (cero falsos positivos): solo se
afirman cuando son matemáticamente seguras. El formato 2026 (12 grupos, avanzan
2 por grupo + 8 mejores terceros) hace la eliminación más exigente, por eso se
verifica contra TODOS los grupos.

Cuando aplica, se muestra una advertencia y se reduce la confianza.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sports_predictor_ml.prediction.soccer_baseline import ContextNote

from ..domain.catalog import Match, MatchStatus

_GROUP_GAMES_PER_TEAM = 3  # round-robin de 4 equipos
_QUALIFYING_THIRDS = 8  # mejores terceros que avanzan en el formato de 48 equipos


class StakesAnalyzer:
    def __init__(self, matches: list[Match], *, qualifying_thirds: int = _QUALIFYING_THIRDS) -> None:
        self._matches = matches
        self._group_of = self._reconstruct_groups(matches)
        self._groups: list[frozenset[str]] = list(set(self._group_of.values()))
        self._qualifying_thirds = qualifying_thirds

    @staticmethod
    def _reconstruct_groups(matches: list[Match]) -> dict[str, frozenset[str]]:
        """Grupos = componentes conexas de 'jugaron entre sí' (fase de grupos)."""
        adjacency: dict[str, set[str]] = defaultdict(set)
        for m in matches:
            adjacency[m.home_team.code].add(m.away_team.code)
            adjacency[m.away_team.code].add(m.home_team.code)

        group_of: dict[str, frozenset[str]] = {}
        seen: set[str] = set()
        for team in adjacency:
            if team in seen:
                continue
            comp: set[str] = set()
            stack = [team]
            while stack:
                t = stack.pop()
                if t in comp:
                    continue
                comp.add(t)
                stack.extend(adjacency[t] - comp)
            frozen = frozenset(comp)
            for t in comp:
                group_of[t] = frozen
            seen |= comp
        return group_of

    def _standings(
        self, group: frozenset[str], as_of: datetime
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Puntos y partidos jugados por equipo, usando SOLO lo jugado antes de as_of."""
        points: dict[str, int] = defaultdict(int)
        played: dict[str, int] = defaultdict(int)
        for m in self._matches:
            if (
                m.status != MatchStatus.FINISHED
                or m.home_score is None
                or m.away_score is None
                or m.kickoff_utc >= as_of
                or m.home_team.code not in group
                or m.away_team.code not in group
            ):
                continue
            h, a = m.home_team.code, m.away_team.code
            played[h] += 1
            played[a] += 1
            if m.home_score > m.away_score:
                points[h] += 3
            elif m.home_score < m.away_score:
                points[a] += 3
            else:
                points[h] += 1
                points[a] += 1
        return points, played

    def context_for(self, match: Match) -> list[ContextNote]:
        notes: list[ContextNote] = []
        for team in (match.home_team, match.away_team):
            group = self._group_of.get(team.code)
            if not group or len(group) < 4:
                continue
            points, played = self._standings(group, match.kickoff_utc)
            if played[team.code] == 0:
                continue

            if self._clinched(team.code, group, points, played):
                notes.append(
                    ContextNote(
                        kind="clinched_qualification",
                        team=team.name,
                        message=(
                            f"{team.name} ya aseguró su clasificación a la siguiente ronda; "
                            "podría rotar o alinear suplentes. El modelo no ve alineaciones, "
                            "así que esta predicción tiene incertidumbre extra."
                        ),
                    )
                )
            elif self._eliminated(team.code, group, points, played, match.kickoff_utc):
                notes.append(
                    ContextNote(
                        kind="eliminated",
                        team=team.name,
                        message=(
                            f"{team.name} ya está eliminado del torneo (no puede clasificar a la "
                            "siguiente ronda); podría rotar o jugar sin presión. El modelo no ve "
                            "alineaciones, así que esta predicción tiene incertidumbre extra."
                        ),
                    )
                )
        return notes

    def _clinched(
        self, team: str, group: frozenset[str], points: dict[str, int], played: dict[str, int]
    ) -> bool:
        """Top-2 garantizado: a lo sumo 1 rival puede alcanzar su peor caso en puntos."""
        team_worst = points[team]
        threats = sum(
            1
            for o in group
            if o != team and points[o] + 3 * (_GROUP_GAMES_PER_TEAM - played[o]) >= team_worst
        )
        return threats <= 1

    def _eliminated(
        self,
        team: str,
        group: frozenset[str],
        points: dict[str, int],
        played: dict[str, int],
        as_of: datetime,
    ) -> bool:
        ceiling = points[team] + 3 * (_GROUP_GAMES_PER_TEAM - played[team])

        # (1) No puede ser top-2: >= 2 rivales ya tienen más puntos que el techo de T.
        out_of_top_two = sum(1 for o in group if o != team and points[o] > ceiling) >= 2
        if not out_of_top_two:
            return False

        # (2) No puede ser mejor tercero: >= 8 grupos producirán un 3er lugar
        # garantizado por encima del techo de T (si un grupo tiene >=3 equipos con
        # más puntos que el techo de T, su tercero superará a T con seguridad).
        better_thirds = 0
        for other in self._groups:
            gp, _ = self._standings(other, as_of)
            if sum(1 for t in other if gp[t] > ceiling) >= 3:
                better_thirds += 1
        return better_thirds >= self._qualifying_thirds
