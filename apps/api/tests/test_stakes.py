"""Pruebas del analizador de 'lo que está en juego' (clasificación asegurada)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.stakes import StakesAnalyzer
from src.domain.catalog import Match, MatchStatus, Sport, Team

_BASE = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)


def _team(code: str) -> Team:
    return Team(code=code, name=code, sport=Sport.SOCCER, short_name=code[:3], is_mock=False)


def _match(mid, home, away, hs, as_, day, status=MatchStatus.FINISHED) -> Match:
    return Match(
        id=mid,
        sport=Sport.SOCCER,
        competition_code="WC_TEST",
        season_label="2026",
        home_team=_team(home),
        away_team=_team(away),
        kickoff_utc=_BASE + timedelta(days=day),
        status=status,
        home_score=hs,
        away_score=as_,
    )


def _scenario() -> StakesAnalyzer:
    # Grupo A,B,C,D. Tras 4 partidos: A=6 (clasificado), B=3, C=1, D=1.
    matches = [
        _match(1, "A", "B", 2, 0, 1),
        _match(2, "A", "C", 1, 0, 2),
        _match(3, "B", "D", 1, 0, 1),
        _match(4, "C", "D", 0, 0, 2),
        # Jornada final (por jugar): A vs D, B vs C.
        _match(5, "A", "D", None, None, 3, MatchStatus.SCHEDULED),
        _match(6, "B", "C", None, None, 3, MatchStatus.SCHEDULED),
    ]
    return StakesAnalyzer(matches)


def test_clinched_team_flagged() -> None:
    analyzer = _scenario()
    target = _match(5, "A", "D", None, None, 3, MatchStatus.SCHEDULED)
    notes = analyzer.context_for(target)
    assert len(notes) == 1
    assert notes[0].team == "A"
    assert notes[0].kind == "clinched_qualification"


def test_non_clinched_match_has_no_context() -> None:
    analyzer = _scenario()
    target = _match(6, "B", "C", None, None, 3, MatchStatus.SCHEDULED)
    assert analyzer.context_for(target) == []


def _elimination_scenario() -> StakesAnalyzer:
    # Grupo 1: X6, Y6, T0, Z0 (T y Z fuera del top-2). Falta T vs Z.
    g1 = [
        _match(1, "X", "T", 1, 0, 1),
        _match(2, "X", "Z", 1, 0, 2),
        _match(3, "Y", "T", 1, 0, 1),
        _match(4, "Y", "Z", 1, 0, 2),
        _match(5, "T", "Z", None, None, 3, MatchStatus.SCHEDULED),
        _match(6, "X", "Y", None, None, 3, MatchStatus.SCHEDULED),
    ]
    # Grupo 2 (completo): P9, Q4, R4, S0 → 3 equipos por encima del techo de T (3).
    g2 = [
        _match(7, "P", "Q", 1, 0, 1),
        _match(8, "P", "R", 1, 0, 1),
        _match(9, "P", "S", 1, 0, 2),
        _match(10, "Q", "S", 1, 0, 2),
        _match(11, "Q", "R", 1, 1, 2),
        _match(12, "R", "S", 1, 0, 2),
    ]
    # Umbral de terceros = 1 para el test (en producción son 8).
    return StakesAnalyzer(g1 + g2, qualifying_thirds=1)


def test_eliminated_team_flagged() -> None:
    analyzer = _elimination_scenario()
    target = _match(5, "T", "Z", None, None, 3, MatchStatus.SCHEDULED)
    notes = analyzer.context_for(target)
    kinds = {(n.team, n.kind) for n in notes}
    assert ("T", "eliminated") in kinds
