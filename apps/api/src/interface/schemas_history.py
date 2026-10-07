"""Schemas del historial de predicciones."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrackRecordResponse(BaseModel):
    n_predictions: int  # total guardadas
    n_resolved: int  # con resultado ya conocido
    accuracy: float
    brier: float
    log_loss: float
    note: str


class StoredProbabilities(BaseModel):
    home: float
    draw: float
    away: float


class StoredPredictionResponse(BaseModel):
    match_id: int
    competition_code: str
    home_name: str
    away_name: str
    kickoff_utc: datetime
    probabilities: StoredProbabilities
    confidence_band: str
    model: str
    resolved: bool
    actual: str | None  # 'H' | 'D' | 'A'
    home_score: int | None
    away_score: int | None
    correct_pick: bool | None


class HistoryResponse(BaseModel):
    items: list[StoredPredictionResponse]
