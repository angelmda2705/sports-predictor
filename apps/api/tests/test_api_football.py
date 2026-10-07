"""Pruebas del parseo de API-Football con payloads de EJEMPLO (no datos reales).

Validan la lógica de parseo sin llamar a la red ni necesitar la API key real.
La forma de los payloads sigue la documentación de API-Football v3.
"""

from __future__ import annotations

from src.infrastructure.providers.api_football import ApiFootballClient

_STATUS_SAMPLE = {
    "response": {
        "account": {"firstname": "Demo", "lastname": "User", "email": "demo@example.com"},
        "subscription": {"plan": "Pro", "end": "2026-12-31", "active": True},
        "requests": {"current": 12, "limit_day": 7500},
    },
    "errors": [],
}

_LINEUPS_SAMPLE = {
    "response": [
        {
            "team": {"id": 2382, "name": "Mexico"},
            "formation": "4-3-3",
            "startXI": [
                {"player": {"id": 1, "name": "G. Ochoa", "number": 13, "pos": "G"}},
                {"player": {"id": 2, "name": "J. Sanchez", "number": 3, "pos": "D"}},
            ],
        }
    ]
}

_INJURIES_SAMPLE = {
    "response": [
        {
            "player": {"id": 5, "name": "R. Jimenez", "type": "Missing Fixture", "reason": "Knee Injury"},
            "team": {"name": "Mexico"},
        }
    ]
}


def test_parse_account() -> None:
    acc = ApiFootballClient.parse_account(_STATUS_SAMPLE)
    assert acc.name == "Demo User"
    assert acc.email == "demo@example.com"
    assert acc.plan == "Pro"
    assert acc.active is True
    assert acc.requests_today == 12
    assert acc.daily_limit == 7500


def test_parse_lineups() -> None:
    lineups = ApiFootballClient.parse_lineups(_LINEUPS_SAMPLE)
    assert len(lineups) == 1
    mx = lineups[0]
    assert mx.team == "Mexico"
    assert mx.formation == "4-3-3"
    assert len(mx.starters) == 2
    assert mx.starters[0].name == "G. Ochoa"
    assert mx.starters[0].number == 13


def test_parse_injuries() -> None:
    injuries = ApiFootballClient.parse_injuries(_INJURIES_SAMPLE)
    assert len(injuries) == 1
    assert injuries[0].player == "R. Jimenez"
    assert injuries[0].team == "Mexico"
    assert injuries[0].reason == "Knee Injury"


_FIXTURE_PLAYERS_SAMPLE = {
    "response": [
        {
            "team": {"id": 26, "name": "Mexico"},
            "players": [
                {
                    "player": {"id": 1, "name": "H. Lozano"},
                    "statistics": [
                        {
                            "games": {
                                "minutes": 78,
                                "rating": "7.4",
                                "position": "F",
                                "substitute": False,
                            },
                            "shots": {"total": 4, "on": 2},
                            "goals": {"total": 1, "assists": 1, "conceded": None, "saves": None},
                            "passes": {"total": 35, "key": 3, "accuracy": "82"},
                            "tackles": {"total": 1, "blocks": 0, "interceptions": 0},
                        }
                    ],
                },
                {
                    "player": {"id": 2, "name": "Banca Total"},
                    "statistics": [
                        {
                            "games": {
                                "minutes": None,
                                "rating": None,
                                "position": "M",
                                "substitute": True,
                            },
                            "shots": {"total": None, "on": None},
                            "goals": {"total": None, "assists": None},
                            "passes": {"total": None, "key": None, "accuracy": None},
                            "tackles": {"total": None, "interceptions": None},
                        }
                    ],
                },
            ],
        }
    ]
}


def test_parse_fixture_players() -> None:
    players = ApiFootballClient.parse_fixture_players(_FIXTURE_PLAYERS_SAMPLE)
    assert len(players) == 2

    lozano = players[0]
    assert lozano.player == "H. Lozano"
    assert lozano.team == "Mexico"
    assert lozano.minutes == 78
    assert lozano.started is True
    assert lozano.rating == 7.4
    assert lozano.goals == 1 and lozano.assists == 1
    assert lozano.shots == 4 and lozano.shots_on == 2
    assert lozano.key_passes == 3
    assert lozano.pass_accuracy == 82.0

    sub = players[1]
    assert sub.started is False  # substitute=True
    assert sub.minutes is None
    assert sub.goals == 0 and sub.shots == 0  # nulos → 0


_FIXTURES_SAMPLE = {
    "response": [
        {
            "fixture": {
                "id": 855739,
                "date": "2022-11-22T16:00:00+00:00",
                "status": {"short": "FT"},
            },
            "league": {"name": "World Cup", "season": 2022},
            "teams": {"home": {"name": "Mexico"}, "away": {"name": "Poland"}},
        },
        {
            "fixture": {
                "id": 999999,
                "date": "2026-06-24T18:00:00+00:00",
                "status": {"short": "NS"},
            },
            "league": {"name": "Friendlies", "season": 2026},
            "teams": {"home": {"name": "Mexico"}, "away": {"name": "Brazil"}},
        },
    ]
}


def test_parse_fixtures() -> None:
    fixtures = ApiFootballClient.parse_fixtures(_FIXTURES_SAMPLE)
    assert len(fixtures) == 2
    fx = fixtures[0]
    assert fx.fixture_id == 855739
    assert fx.kickoff.startswith("2022-11-22")
    assert fx.league == "World Cup"
    assert fx.season == 2022
    assert fx.home == "Mexico" and fx.away == "Poland"
    assert fx.status == "FT"
    assert fixtures[1].status == "NS"  # partido sin jugar


def test_client_requires_key() -> None:
    import pytest

    with pytest.raises(ValueError):
        ApiFootballClient("")


def test_providers_status_not_configured(client) -> None:
    # Sin key configurada, el endpoint debe responder configured=False.
    r = client.get("/providers/status")
    assert r.status_code == 200
    prov = r.json()["providers"][0]
    assert prov["name"] == "api-football"
    assert prov["configured"] is False
    assert prov["connected"] is False
