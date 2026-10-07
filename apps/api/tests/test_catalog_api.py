"""Pruebas de integración de los endpoints de catálogo (datos mock)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_competitions_all_mock(client: TestClient) -> None:
    r = client.get("/competitions")
    assert r.status_code == 200
    comps = r.json()
    codes = {c["code"] for c in comps}
    assert {"ENG_PL", "NFL"} <= codes
    assert all(c["is_mock"] for c in comps)


def test_filter_competitions_by_sport(client: TestClient) -> None:
    r = client.get("/competitions", params={"sport": "soccer"})
    assert r.status_code == 200
    assert {c["code"] for c in r.json()} == {"ENG_PL", "WC_2026"}


def test_world_cup_present_and_mock(client: TestClient) -> None:
    comp = client.get("/competitions/WC_2026")
    assert comp.status_code == 200
    assert comp.json()["is_mock"] is True

    teams = client.get("/competitions/WC_2026/teams").json()
    assert len(teams) == 8
    names = {t["name"] for t in teams}
    assert "México" in names


def test_world_cup_matches_have_stage(client: TestClient) -> None:
    body = client.get("/matches", params={"competition": "WC_2026", "limit": 100}).json()
    assert body["total"] == 12  # 2 grupos x 6 partidos round-robin
    assert all(m["competition_code"] == "WC_2026" for m in body["items"])
    assert all(m["stage"] and "Fase de grupos" in m["stage"] for m in body["items"])


def test_world_cup_has_upcoming_matches(client: TestClient) -> None:
    body = client.get(
        "/matches",
        params={"competition": "WC_2026", "status": "scheduled", "limit": 100},
    ).json()
    assert body["total"] > 0  # hay próximos partidos del Mundial


def test_get_competition_found_and_not_found(client: TestClient) -> None:
    assert client.get("/competitions/ENG_PL").status_code == 200
    assert client.get("/competitions/NOPE").status_code == 404


def test_list_teams_of_competition(client: TestClient) -> None:
    r = client.get("/competitions/ENG_PL/teams")
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) == 8
    assert all(t["is_mock"] and t["sport"] == "soccer" for t in teams)


def test_list_teams_unknown_competition_404(client: TestClient) -> None:
    assert client.get("/competitions/NOPE/teams").status_code == 404


def test_get_team_found_and_not_found(client: TestClient) -> None:
    assert client.get("/teams/ENG_ARS").status_code == 200
    assert client.get("/teams/ENG_ARS").json()["name"] == "Arsenal"
    assert client.get("/teams/NOPE").status_code == 404


def test_matches_envelope_and_mock_flag(client: TestClient) -> None:
    r = client.get("/matches")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert body["contains_mock"] is True
    assert len(body["items"]) <= body["limit"]


def test_matches_filter_by_competition(client: TestClient) -> None:
    body = client.get("/matches", params={"competition": "ENG_PL", "limit": 100}).json()
    assert body["total"] > 0
    assert all(m["competition_code"] == "ENG_PL" for m in body["items"])


def test_matches_filter_by_status(client: TestClient) -> None:
    body = client.get("/matches", params={"status": "scheduled", "limit": 100}).json()
    assert body["total"] > 0
    assert all(m["status"] == "scheduled" for m in body["items"])
    assert all(m["home_score"] is None for m in body["items"])


def test_matches_filter_by_team(client: TestClient) -> None:
    body = client.get("/matches", params={"team": "ENG_ARS", "limit": 100}).json()
    assert body["total"] > 0
    for m in body["items"]:
        assert "ENG_ARS" in (m["home_team"]["code"], m["away_team"]["code"])


def test_matches_search_by_name(client: TestClient) -> None:
    body = client.get("/matches", params={"q": "Arsenal", "limit": 100}).json()
    assert body["total"] > 0
    for m in body["items"]:
        assert "Arsenal" in (m["home_team"]["name"], m["away_team"]["name"])


def test_matches_pagination(client: TestClient) -> None:
    first = client.get("/matches", params={"limit": 5, "offset": 0}).json()
    second = client.get("/matches", params={"limit": 5, "offset": 5}).json()
    assert len(first["items"]) == 5
    assert first["total"] == second["total"]
    first_ids = {m["id"] for m in first["items"]}
    second_ids = {m["id"] for m in second["items"]}
    assert first_ids.isdisjoint(second_ids)  # páginas sin solape


def test_matches_date_range_filter(client: TestClient) -> None:
    # Solo partidos de la temporada 2026 en adelante (programados).
    body = client.get("/matches", params={"date_from": "2026-07-01", "limit": 100}).json()
    assert body["total"] > 0
    assert all(m["kickoff_utc"] >= "2026-07-01" for m in body["items"])


def test_matches_order_desc(client: TestClient) -> None:
    asc = client.get("/matches", params={"order": "asc", "limit": 100}).json()["items"]
    desc = client.get("/matches", params={"order": "desc", "limit": 100}).json()["items"]
    # El primero en desc debe ser de fecha >= que el primero en asc.
    assert desc[0]["kickoff_utc"] >= asc[0]["kickoff_utc"]
    assert desc[0]["id"] != asc[0]["id"]


def test_get_match_by_id_and_404(client: TestClient) -> None:
    any_match = client.get("/matches", params={"limit": 1}).json()["items"][0]
    r = client.get(f"/matches/{any_match['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == any_match["id"]
    assert client.get("/matches/99999").status_code == 404
