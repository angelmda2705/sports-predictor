"""Pruebas del servicio de predicción de jugadores con un cliente FALSO (sin red).

Validan el armado del historial, el filtrado de partidos terminados, la elección
del jugador correcto ante coincidencias por substring y los errores de no-encontrado.
No requieren la API key ni internet.
"""

from __future__ import annotations

import pytest

from src.application.player_service import PlayerNotFound, PlayerService
from src.infrastructure.providers.api_football import FixtureRef, PlayerMatchStats


def _stats(player: str, team: str, *, minutes, started, goals=0, assists=0, shots=0) -> PlayerMatchStats:
    return PlayerMatchStats(
        player=player,
        team=team,
        minutes=minutes,
        started=started,
        position="F",
        rating=7.0 if minutes else None,
        goals=goals,
        assists=assists,
        shots=shots,
        shots_on=min(shots, 1),
        key_passes=1,
        passes=20,
        pass_accuracy=80.0,
        tackles=0,
        interceptions=0,
    )


def _fx(fid: int, date: str, home: str, away: str, status: str = "FT") -> FixtureRef:
    return FixtureRef(
        fixture_id=fid,
        kickoff=date,
        league="World Cup",
        season=2022,
        home=home,
        away=away,
        status=status,
    )


class FakeClient:
    """Cliente de API-Football simulado: devuelve datos canónicos sin tocar la red."""

    def __init__(self, *, team_id, fixtures, players_by_fixture) -> None:
        self._team_id = team_id
        self._fixtures = fixtures
        self._players_by_fixture = players_by_fixture
        self.fixture_calls: list[int] = []

    def find_team_id(self, name, *, national=None):
        return self._team_id

    def team_fixtures(self, team_id, season, *, league=None):
        return self._fixtures

    def fixture_player_stats(self, fixture_id):
        self.fixture_calls.append(fixture_id)
        return self._players_by_fixture.get(fixture_id, [])


def test_predicts_regular_starter_from_real_like_logs() -> None:
    fixtures = [
        _fx(1, "2022-11-22T16:00:00+00:00", "Mexico", "Poland"),
        _fx(2, "2022-11-26T19:00:00+00:00", "Argentina", "Mexico"),
        _fx(3, "2022-11-30T19:00:00+00:00", "Saudi Arabia", "Mexico"),
        _fx(4, "2026-06-24T18:00:00+00:00", "Mexico", "Brazil", status="NS"),  # no jugado
    ]
    players = {
        1: [_stats("H. Lozano", "Mexico", minutes=78, started=True, goals=1, shots=3)],
        2: [_stats("H. Lozano", "Mexico", minutes=90, started=True, goals=0, shots=2)],
        3: [_stats("H. Lozano", "Mexico", minutes=65, started=True, goals=1, shots=4)],
        4: [_stats("H. Lozano", "Mexico", minutes=None, started=False)],  # no debe contar
    }
    svc = PlayerService(FakeClient(team_id=16, fixtures=fixtures, players_by_fixture=players))

    result = svc.predict("Lozano", "Mexico", season=2022, league=1)

    assert result.player == "H. Lozano"
    assert result.team == "Mexico"
    assert result.n_fixtures_scanned == 3  # el NS no se cuenta
    assert len(result.games) == 3
    # Ordenado por fecha ascendente.
    assert [g.date for g in result.games] == ["2022-11-22", "2022-11-26", "2022-11-30"]
    # Oponente calculado según el lado del jugador.
    assert result.games[0].opponent == "Poland"
    assert result.games[1].opponent == "Argentina"
    # Predicción coherente: titular siempre → prob_start alta.
    assert result.prediction.prob_start > 0.9
    assert result.prediction.expected_minutes > 60


def test_substring_picks_player_with_more_games() -> None:
    fixtures = [
        _fx(1, "2022-11-22T16:00:00+00:00", "Mexico", "Poland"),
        _fx(2, "2022-11-26T19:00:00+00:00", "Argentina", "Mexico"),
    ]
    players = {
        1: [
            _stats("J. Sanchez", "Mexico", minutes=90, started=True),
            _stats("A. Sanchez", "Mexico", minutes=20, started=False),
        ],
        2: [_stats("J. Sanchez", "Mexico", minutes=90, started=True)],
    }
    svc = PlayerService(FakeClient(team_id=16, fixtures=fixtures, players_by_fixture=players))

    result = svc.predict("Sanchez", "Mexico", season=2022)
    # "J. Sanchez" aparece 2 veces, "A. Sanchez" 1 → se elige el de más apariciones.
    assert result.player == "J. Sanchez"
    assert len(result.games) == 2


def test_player_not_found_raises() -> None:
    fixtures = [_fx(1, "2022-11-22T16:00:00+00:00", "Mexico", "Poland")]
    players = {1: [_stats("H. Lozano", "Mexico", minutes=90, started=True)]}
    svc = PlayerService(FakeClient(team_id=16, fixtures=fixtures, players_by_fixture=players))

    with pytest.raises(PlayerNotFound):
        svc.predict("Messi", "Mexico", season=2022)


def test_team_not_found_raises() -> None:
    class NoTeam(FakeClient):
        def find_team_id(self, name, *, national=None):
            return None

    svc = PlayerService(NoTeam(team_id=None, fixtures=[], players_by_fixture={}))
    with pytest.raises(PlayerNotFound):
        svc.predict("Lozano", "Narnia", season=2022)


def test_only_finished_fixtures_are_fetched() -> None:
    fixtures = [
        _fx(1, "2022-11-22T16:00:00+00:00", "Mexico", "Poland"),
        _fx(2, "2026-06-24T18:00:00+00:00", "Mexico", "Brazil", status="NS"),
    ]
    players = {1: [_stats("H. Lozano", "Mexico", minutes=90, started=True)]}
    client = FakeClient(team_id=16, fixtures=fixtures, players_by_fixture=players)
    svc = PlayerService(client)

    svc.predict("Lozano", "Mexico", season=2022)
    # Solo se consultó el partido terminado (cuota: no se pide el NS).
    assert client.fixture_calls == [1]
