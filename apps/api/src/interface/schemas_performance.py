"""Schemas de respuesta del dashboard de rendimiento del modelo."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sports_predictor_ml.evaluation.metrics import PerformanceReport


class CalibrationBinResponse(BaseModel):
    lower: float
    upper: float
    mean_predicted: float
    observed_frequency: float
    count: int


class BandPerformanceResponse(BaseModel):
    band: str
    n: int
    accuracy: float
    brier: float


class PerformanceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    n_predictions: int
    accuracy: float
    brier: float
    log_loss: float
    baseline_brier: float
    baseline_log_loss: float
    beats_baseline: bool
    ece: float
    calibration: list[CalibrationBinResponse]
    by_band: list[BandPerformanceResponse]
    is_mock: bool
    disclaimer: str

    @classmethod
    def from_report(
        cls, report: PerformanceReport, *, is_mock: bool
    ) -> PerformanceResponse:
        return cls(
            model_name="soccer_elo_baseline",
            n_predictions=report.n,
            accuracy=report.accuracy,
            brier=report.brier,
            log_loss=report.log_loss,
            baseline_brier=report.baseline_brier,
            baseline_log_loss=report.baseline_log_loss,
            # Mejor que el baseline ingenuo si su Brier es menor (menor = mejor).
            beats_baseline=report.n > 0 and report.brier < report.baseline_brier,
            ece=report.ece,
            calibration=[
                CalibrationBinResponse(
                    lower=b.lower,
                    upper=b.upper,
                    mean_predicted=round(b.mean_predicted, 4),
                    observed_frequency=round(b.observed_frequency, 4),
                    count=b.count,
                )
                for b in report.calibration
            ],
            by_band=[
                BandPerformanceResponse(band=b.band, n=b.n, accuracy=b.accuracy, brier=b.brier)
                for b in report.by_band
            ],
            is_mock=is_mock,
            disclaimer=(
                "Backtest walk-forward (point-in-time) del modelo baseline. "
                + ("Sobre DATOS MOCK de demostración. " if is_mock else "")
                + "No se ocultan predicciones fallidas; el rendimiento pasado no "
                "garantiza resultados futuros."
            ),
        )
