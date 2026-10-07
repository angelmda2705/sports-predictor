"""Endpoints del historial de predicciones (track record real, durable)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ...application.prediction_history import PredictionHistoryRepository
from ..schemas_history import (
    HistoryResponse,
    StoredPredictionResponse,
    StoredProbabilities,
    TrackRecordResponse,
)

router = APIRouter(tags=["history"])


def _repo(request: Request) -> PredictionHistoryRepository:
    return request.app.state.history_repo


@router.get("/predictions/track-record", response_model=TrackRecordResponse)
def track_record(
    request: Request, competition: str | None = Query(default=None)
) -> TrackRecordResponse:
    tr = _repo(request).track_record(competition_code=competition)
    return TrackRecordResponse(
        n_predictions=tr.n_predictions,
        n_resolved=tr.n_resolved,
        accuracy=tr.accuracy,
        brier=tr.brier,
        log_loss=tr.log_loss,
        note=(
            "Historial GUARDADO de predicciones point-in-time (lo que se sabía antes de "
            "cada partido). No se ocultan fallos. Modelo baseline; sobre datos mock/real "
            "según corresponda."
        ),
    )


@router.get("/predictions/recent", response_model=HistoryResponse)
def recent(
    request: Request,
    competition: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> HistoryResponse:
    views = _repo(request).recent(competition_code=competition, limit=limit)
    return HistoryResponse(
        items=[
            StoredPredictionResponse(
                match_id=v.match_id,
                competition_code=v.competition_code,
                home_name=v.home_name,
                away_name=v.away_name,
                kickoff_utc=v.kickoff,
                probabilities=StoredProbabilities(
                    home=v.prob_home, draw=v.prob_draw, away=v.prob_away
                ),
                confidence_band=v.confidence_band,
                model=f"{v.model_name} v{v.model_version}",
                resolved=v.resolved,
                actual=v.actual,
                home_score=v.home_score,
                away_score=v.away_score,
                correct_pick=v.correct_pick,
            )
            for v in views
        ]
    )
