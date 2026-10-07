"""Pruebas de integración del endpoint de predicción."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _a_scheduled_soccer_match(client: TestClient, competition: str) -> int:
    body = client.get(
        "/matches",
        params={"competition": competition, "status": "scheduled", "limit": 1},
    ).json()
    assert body["items"], f"no hay partidos programados en {competition}"
    return body["items"][0]["id"]


def test_prediction_shape_for_world_cup(client: TestClient) -> None:
    match_id = _a_scheduled_soccer_match(client, "WC_2026")
    r = client.get(f"/matches/{match_id}/prediction")
    assert r.status_code == 200
    body = r.json()

    # Probabilidades 1X2 válidas y suman ~1.
    p = body["probabilities"]
    total = p["home"] + p["draw"] + p["away"]
    assert abs(total - 1.0) < 1e-3
    for v in p.values():
        assert 0.0 <= v <= 1.0

    assert body["model"]["name"] == "soccer_elo_baseline"
    assert body["confidence"]["band"] in {"baja", "media", "alta"}
    assert "criterion" in body["confidence"]
    assert body["is_mock"] is True
    assert "mock" in body["disclaimer"].lower()
    assert len(body["factors"]) >= 1


def test_prediction_works_for_premier_league(client: TestClient) -> None:
    match_id = _a_scheduled_soccer_match(client, "ENG_PL")
    r = client.get(f"/matches/{match_id}/prediction")
    assert r.status_code == 200
    assert r.json()["expected_goals"]["home"] >= 0


def test_prediction_404_for_unknown_match(client: TestClient) -> None:
    assert client.get("/matches/999999/prediction").status_code == 404


def test_prediction_422_for_american_football(client: TestClient) -> None:
    match_id = _a_scheduled_soccer_match(client, "NFL")
    r = client.get(f"/matches/{match_id}/prediction")
    assert r.status_code == 422
    assert "soccer" in r.json()["detail"].lower()


def test_prediction_is_reproducible(client: TestClient) -> None:
    match_id = _a_scheduled_soccer_match(client, "WC_2026")
    first = client.get(f"/matches/{match_id}/prediction").json()
    second = client.get(f"/matches/{match_id}/prediction").json()
    assert first["probabilities"] == second["probabilities"]
    assert first["confidence"] == second["confidence"]
