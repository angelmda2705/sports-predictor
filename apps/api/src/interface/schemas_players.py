"""Schemas de la predicción individual de jugadores (datos reales API-Football)."""

from __future__ import annotations

from pydantic import BaseModel


class PlayerGameRowOut(BaseModel):
    date: str
    opponent: str
    started: bool
    minutes: int
    goals: int
    assists: int
    shots: int


class PlayerPredictionOut(BaseModel):
    n_games: int
    prob_start: float
    expected_minutes: float
    expected_goals: float
    expected_assists: float
    expected_shots: float
    expected_shots_on: float
    prob_scores: float  # P(al menos 1 gol)
    confidence: float
    confidence_band: str  # baja | media | alta
    low_confidence_note: str | None
    factors: list[str]


class PlayerPredictionResponse(BaseModel):
    player: str
    team: str
    season: int
    n_fixtures_scanned: int
    games: list[PlayerGameRowOut]
    prediction: PlayerPredictionOut
    disclaimer: str
