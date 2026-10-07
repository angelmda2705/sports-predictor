"""Repositorio SQLAlchemy del historial de predicciones (SQLite/Postgres)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sports_predictor_ml.evaluation.metrics import BacktestSample, brier_score, log_loss

from ...application.prediction_history import (
    MatchPredictionRecord,
    StoredPredictionView,
    TrackRecord,
)
from .prediction_models import (
    ModelVersionRow,
    PredBase,
    PredictionOutcomeRow,
    PredictionRow,
)

_OUTCOMES = ("H", "D", "A")


def _argmax_outcome(ph: float, pd: float, pa: float) -> str:
    probs = (ph, pd, pa)
    return _OUTCOMES[max(range(3), key=lambda i: probs[i])]


class SqlAlchemyPredictionHistory:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def create_tables(self, engine: Engine) -> None:
        PredBase.metadata.create_all(engine)

    def count(self) -> int:
        with self._sf() as s:
            return int(s.scalar(select(func.count()).select_from(PredictionRow)) or 0)

    def _model_version_id(self, s: Session, name: str, version: str) -> int:
        row = s.scalar(
            select(ModelVersionRow).where(
                ModelVersionRow.name == name, ModelVersionRow.version == version
            )
        )
        if row is None:
            row = ModelVersionRow(name=name, version=version, created_at=datetime.now(UTC))
            s.add(row)
            s.flush()
        return row.id

    def store_many(self, records: list[MatchPredictionRecord]) -> int:
        stored = 0
        with self._sf() as s:
            for r in records:
                mv_id = self._model_version_id(s, r.model_name, r.model_version)
                existing = s.scalar(
                    select(PredictionRow).where(
                        PredictionRow.match_id == r.match_id,
                        PredictionRow.model_version_id == mv_id,
                    )
                )
                if existing is not None:
                    continue
                pred = PredictionRow(
                    match_id=r.match_id,
                    model_version_id=mv_id,
                    competition_code=r.competition_code,
                    home_name=r.home_name,
                    away_name=r.away_name,
                    kickoff_utc=r.kickoff,
                    prob_home=r.prob_home,
                    prob_draw=r.prob_draw,
                    prob_away=r.prob_away,
                    confidence=r.confidence,
                    confidence_band=r.confidence_band,
                    is_mock=r.is_mock,
                    created_at=datetime.now(UTC),
                )
                s.add(pred)
                s.flush()
                stored += 1

                if r.actual is not None and r.home_score is not None and r.away_score is not None:
                    sample = BacktestSample(
                        r.prob_home, r.prob_draw, r.prob_away, r.actual, r.confidence_band,
                        r.competition_code,
                    )
                    correct = _argmax_outcome(r.prob_home, r.prob_draw, r.prob_away) == r.actual
                    s.add(
                        PredictionOutcomeRow(
                            prediction_id=pred.id,
                            actual=r.actual,
                            home_score=r.home_score,
                            away_score=r.away_score,
                            brier=brier_score([sample]),
                            log_loss=log_loss([sample]),
                            correct_pick=correct,
                            resolved_at=datetime.now(UTC),
                        )
                    )
            s.commit()
        return stored

    def recent(
        self, *, competition_code: str | None = None, limit: int = 50
    ) -> list[StoredPredictionView]:
        with self._sf() as s:
            stmt = (
                select(PredictionRow, PredictionOutcomeRow, ModelVersionRow)
                .join(ModelVersionRow, PredictionRow.model_version_id == ModelVersionRow.id)
                .outerjoin(PredictionOutcomeRow, PredictionOutcomeRow.prediction_id == PredictionRow.id)
                .order_by(PredictionRow.kickoff_utc.desc())
                .limit(limit)
            )
            if competition_code:
                stmt = stmt.where(PredictionRow.competition_code == competition_code)
            out: list[StoredPredictionView] = []
            for pred, outcome, mv in s.execute(stmt):
                out.append(
                    StoredPredictionView(
                        match_id=pred.match_id,
                        competition_code=pred.competition_code,
                        home_name=pred.home_name,
                        away_name=pred.away_name,
                        kickoff=pred.kickoff_utc,
                        prob_home=pred.prob_home,
                        prob_draw=pred.prob_draw,
                        prob_away=pred.prob_away,
                        confidence_band=pred.confidence_band,
                        model_name=mv.name,
                        model_version=mv.version,
                        resolved=outcome is not None,
                        actual=outcome.actual if outcome else None,
                        home_score=outcome.home_score if outcome else None,
                        away_score=outcome.away_score if outcome else None,
                        correct_pick=outcome.correct_pick if outcome else None,
                    )
                )
            return out

    def track_record(self, *, competition_code: str | None = None) -> TrackRecord:
        with self._sf() as s:
            base = select(PredictionRow.id)
            if competition_code:
                base = base.where(PredictionRow.competition_code == competition_code)
            n_predictions = int(s.scalar(select(func.count()).select_from(base.subquery())) or 0)

            ostmt = select(
                func.count(),
                func.avg(PredictionOutcomeRow.correct_pick),
                func.avg(PredictionOutcomeRow.brier),
                func.avg(PredictionOutcomeRow.log_loss),
            ).join(PredictionRow, PredictionRow.id == PredictionOutcomeRow.prediction_id)
            if competition_code:
                ostmt = ostmt.where(PredictionRow.competition_code == competition_code)
            n_resolved, acc, brier, ll = s.execute(ostmt).one()

            return TrackRecord(
                n_predictions=n_predictions,
                n_resolved=int(n_resolved or 0),
                accuracy=round(float(acc), 4) if acc is not None else 0.0,
                brier=round(float(brier), 4) if brier is not None else 0.0,
                log_loss=round(float(ll), 4) if ll is not None else 0.0,
            )
