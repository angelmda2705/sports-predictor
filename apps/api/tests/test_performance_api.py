"""Pruebas de integración del dashboard de rendimiento."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_performance_overall(client: TestClient) -> None:
    r = client.get("/performance")
    assert r.status_code == 200
    body = r.json()
    assert body["n_predictions"] > 0
    assert 0.0 <= body["accuracy"] <= 1.0
    assert body["brier"] >= 0.0
    assert body["log_loss"] >= 0.0
    assert "baseline_brier" in body
    assert isinstance(body["beats_baseline"], bool)
    assert body["is_mock"] is True
    assert "mock" in body["disclaimer"].lower()


def test_performance_calibration_present(client: TestClient) -> None:
    body = client.get("/performance").json()
    # La calibración agrupa 3 puntos (clases) por predicción.
    total_points = sum(b["count"] for b in body["calibration"])
    assert total_points == 3 * body["n_predictions"]
    assert 0.0 <= body["ece"] <= 1.0


def test_performance_filtered_by_competition(client: TestClient) -> None:
    body = client.get("/performance", params={"competition": "WC_2026"}).json()
    assert body["n_predictions"] > 0  # el Mundial tiene partidos finalizados (J1/J2)


def test_performance_by_band_consistent(client: TestClient) -> None:
    body = client.get("/performance").json()
    total_band_n = sum(b["n"] for b in body["by_band"])
    assert total_band_n == body["n_predictions"]
