"""Modelos SQLAlchemy para persistir predicciones, su versión de modelo y su resultado.

Refleja el §5.3 del documento técnico (model_version / prediction / prediction_outcome).
Tipos portables → corre igual en SQLite (local) y Postgres (producción).

Reproducibilidad (§18): cada predicción queda ligada a una versión de modelo.
Transparencia (§12): los resultados NO se borran ni se ocultan.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PredBase(DeclarativeBase):
    pass


class ModelVersionRow(PredBase):
    __tablename__ = "model_version"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_name_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PredictionRow(PredBase):
    __tablename__ = "prediction"
    __table_args__ = (UniqueConstraint("match_id", "model_version_id", name="uq_match_model"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_version.id"), nullable=False)
    competition_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    home_name: Mapped[str] = mapped_column(String(80), nullable=False)
    away_name: Mapped[str] = mapped_column(String(80), nullable=False)
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prob_home: Mapped[float] = mapped_column(Float, nullable=False)
    prob_draw: Mapped[float] = mapped_column(Float, nullable=False)
    prob_away: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(8), nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PredictionOutcomeRow(PredBase):
    __tablename__ = "prediction_outcome"

    prediction_id: Mapped[int] = mapped_column(ForeignKey("prediction.id"), primary_key=True)
    actual: Mapped[str] = mapped_column(String(1), nullable=False)  # 'H' | 'D' | 'A'
    home_score: Mapped[int] = mapped_column(Integer, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False)
    brier: Mapped[float] = mapped_column(Float, nullable=False)
    log_loss: Mapped[float] = mapped_column(Float, nullable=False)
    correct_pick: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
