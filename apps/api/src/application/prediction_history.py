"""Historial de predicciones: DTOs y puerto del repositorio (capa de aplicación).

Guardar cada predicción con su versión de modelo (reproducibilidad §18) y, cuando
el partido termina, su resultado real (transparencia §11/§12). La infraestructura
implementa el puerto contra SQLite (local) o Postgres (producción).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MatchPredictionRecord:
    """Predicción a persistir. ``actual`` se rellena solo si el partido ya terminó."""

    match_id: int
    competition_code: str
    home_name: str
    away_name: str
    kickoff: datetime
    prob_home: float
    prob_draw: float
    prob_away: float
    confidence: float
    confidence_band: str
    model_name: str
    model_version: str
    is_mock: bool
    actual: str | None = None  # 'H' | 'D' | 'A'
    home_score: int | None = None
    away_score: int | None = None


@dataclass(frozen=True)
class StoredPredictionView:
    """Predicción guardada (con su resultado si ya se resolvió), para mostrar."""

    match_id: int
    competition_code: str
    home_name: str
    away_name: str
    kickoff: datetime
    prob_home: float
    prob_draw: float
    prob_away: float
    confidence_band: str
    model_name: str
    model_version: str
    resolved: bool
    actual: str | None
    home_score: int | None
    away_score: int | None
    correct_pick: bool | None


@dataclass(frozen=True)
class TrackRecord:
    """Desempeño agregado del historial GUARDADO (no se ocultan fallos)."""

    n_predictions: int
    n_resolved: int
    accuracy: float
    brier: float
    log_loss: float


class PredictionHistoryRepository(Protocol):
    def count(self) -> int: ...

    def store_many(self, records: list[MatchPredictionRecord]) -> int: ...

    def recent(
        self, *, competition_code: str | None = None, limit: int = 50
    ) -> list[StoredPredictionView]: ...

    def track_record(self, *, competition_code: str | None = None) -> TrackRecord: ...
