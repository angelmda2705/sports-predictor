"""Pruebas del historial de predicciones (repositorio + endpoints + poblado)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.application.populate_history import populate
from src.application.prediction_history import MatchPredictionRecord
from src.infrastructure.db.engine import build_inmemory_engine, build_session_factory
from src.infrastructure.db.prediction_repository import SqlAlchemyPredictionHistory

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _repo() -> SqlAlchemyPredictionHistory:
    engine = build_inmemory_engine()
    repo = SqlAlchemyPredictionHistory(build_session_factory(engine))
    repo.create_tables(engine)
    return repo


def _rec(mid, ph, pd, pa, actual, hs=None, as_=None, day=0):
    return MatchPredictionRecord(
        match_id=mid,
        competition_code="WC_2026",
        home_name=f"H{mid}",
        away_name=f"A{mid}",
        kickoff=_BASE + timedelta(days=day),
        prob_home=ph,
        prob_draw=pd,
        prob_away=pa,
        confidence=0.3,
        confidence_band="media",
        model_name="soccer_elo_baseline",
        model_version="0.1.0",
        is_mock=False,
        actual=actual,
        home_score=hs,
        away_score=as_,
    )


def test_store_and_track_record() -> None:
    repo = _repo()
    n = repo.store_many(
        [
            _rec(1, 0.6, 0.2, 0.2, "H", 2, 0, day=1),  # acierto (favorito local gana)
            _rec(2, 0.2, 0.2, 0.6, "H", 1, 0, day=2),  # fallo (predijo visita, gano local)
            _rec(3, 0.5, 0.3, 0.2, None, day=3),  # próximo, sin resultado
        ]
    )
    assert n == 3
    assert repo.count() == 3

    tr = repo.track_record()
    assert tr.n_predictions == 3
    assert tr.n_resolved == 2
    assert tr.accuracy == 0.5  # 1 de 2 acertados
    assert tr.brier > 0.0


def test_store_is_idempotent() -> None:
    repo = _repo()
    rec = _rec(1, 0.6, 0.2, 0.2, "H", 2, 0)
    assert repo.store_many([rec]) == 1
    assert repo.store_many([rec]) == 0  # mismo (match, modelo) no se duplica
    assert repo.count() == 1


def test_recent_orders_desc_and_marks_unresolved() -> None:
    repo = _repo()
    repo.store_many([_rec(1, 0.6, 0.2, 0.2, "H", 2, 0, day=1), _rec(2, 0.5, 0.3, 0.2, None, day=5)])
    views = repo.recent(limit=10)
    assert views[0].match_id == 2  # más reciente primero
    assert views[0].resolved is False
    assert views[1].resolved is True


def test_history_endpoints_empty(client: TestClient) -> None:
    tr = client.get("/predictions/track-record").json()
    assert tr["n_predictions"] == 0
    assert client.get("/predictions/recent").json()["items"] == []


def test_populate_then_query(client: TestClient) -> None:
    app = client.app
    n = populate(
        app.state.catalog_repo,
        app.state.backtest_service,
        app.state.prediction_service,
        app.state.history_repo,
    )
    assert n > 0
    tr = client.get("/predictions/track-record").json()
    assert tr["n_predictions"] == n
    assert tr["n_resolved"] > 0
    items = client.get("/predictions/recent", params={"limit": 5}).json()["items"]
    assert 0 < len(items) <= 5
