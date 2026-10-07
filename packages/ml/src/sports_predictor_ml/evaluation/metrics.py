"""Métricas de evaluación para predicciones 1X2 (clasificación de 3 clases).

Todas son funciones puras sobre una lista de ``BacktestSample`` (probabilidad
predicha + resultado real). No inventan nada: miden el desempeño observado.

Incluye comparación contra un **baseline ingenuo** (frecuencias base de los
resultados) para que el desempeño del modelo se juzgue contra una referencia
honesta, no en el vacío.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_OUTCOMES = ("H", "D", "A")
_EPS = 1e-15


@dataclass(frozen=True)
class BacktestSample:
    p_home: float
    p_draw: float
    p_away: float
    actual: str  # 'H' | 'D' | 'A'
    confidence_band: str
    competition_code: str

    def probs(self) -> tuple[float, float, float]:
        return (self.p_home, self.p_draw, self.p_away)

    def onehot(self) -> tuple[int, int, int]:
        return tuple(1 if o == self.actual else 0 for o in _OUTCOMES)  # type: ignore[return-value]

    def predicted_outcome(self) -> str:
        return _OUTCOMES[max(range(3), key=lambda i: self.probs()[i])]


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    mean_predicted: float
    observed_frequency: float
    count: int


@dataclass(frozen=True)
class BandPerformance:
    band: str
    n: int
    accuracy: float
    brier: float


@dataclass(frozen=True)
class PerformanceReport:
    n: int
    accuracy: float
    brier: float
    log_loss: float
    baseline_brier: float
    baseline_log_loss: float
    ece: float
    calibration: list[CalibrationBin]
    by_band: list[BandPerformance]


def brier_score(samples: list[BacktestSample]) -> float:
    """Brier multiclase: media de Σ_k (p_k − y_k)². Menor es mejor (0 = perfecto)."""
    if not samples:
        return 0.0
    total = 0.0
    for s in samples:
        total += sum((p - y) ** 2 for p, y in zip(s.probs(), s.onehot(), strict=True))
    return total / len(samples)


def log_loss(samples: list[BacktestSample]) -> float:
    """Log loss multiclase: −media(log p_real). Menor es mejor."""
    if not samples:
        return 0.0
    total = 0.0
    for s in samples:
        p_actual = s.probs()[_OUTCOMES.index(s.actual)]
        total += -math.log(min(max(p_actual, _EPS), 1.0))
    return total / len(samples)


def accuracy(samples: list[BacktestSample]) -> float:
    """Fracción de partidos donde el resultado más probable fue el real."""
    if not samples:
        return 0.0
    hits = sum(1 for s in samples if s.predicted_outcome() == s.actual)
    return hits / len(samples)


def _base_rates(samples: list[BacktestSample]) -> tuple[float, float, float]:
    n = len(samples)
    counts = [sum(1 for s in samples if s.actual == o) for o in _OUTCOMES]
    return tuple(c / n for c in counts)  # type: ignore[return-value]


def _constant_prediction_samples(
    samples: list[BacktestSample], probs: tuple[float, float, float]
) -> list[BacktestSample]:
    return [
        BacktestSample(probs[0], probs[1], probs[2], s.actual, s.confidence_band, s.competition_code)
        for s in samples
    ]


def calibration(samples: list[BacktestSample], n_bins: int = 5) -> tuple[list[CalibrationBin], float]:
    """Diagrama de confiabilidad y ECE.

    Trata cada par (probabilidad de una clase, ¿ocurrió esa clase?) como un punto
    binario, agrupa los 3·n puntos por probabilidad predicha y compara la media
    predicha contra la frecuencia observada. ECE = error de calibración esperado
    (promedio ponderado |predicho − observado|).
    """
    points: list[tuple[float, int]] = []
    for s in samples:
        for p, y in zip(s.probs(), s.onehot(), strict=True):
            points.append((p, y))
    if not points:
        return [], 0.0

    bins: list[CalibrationBin] = []
    ece = 0.0
    total = len(points)
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        # El último bin incluye el extremo superior.
        in_bin = [
            (p, y) for p, y in points if (lo <= p < hi or (b == n_bins - 1 and p == hi))
        ]
        if not in_bin:
            continue
        mean_pred = sum(p for p, _ in in_bin) / len(in_bin)
        obs_freq = sum(y for _, y in in_bin) / len(in_bin)
        bins.append(CalibrationBin(lo, hi, mean_pred, obs_freq, len(in_bin)))
        ece += (len(in_bin) / total) * abs(mean_pred - obs_freq)
    return bins, ece


def _by_band(samples: list[BacktestSample]) -> list[BandPerformance]:
    out: list[BandPerformance] = []
    for band in ("baja", "media", "alta"):
        group = [s for s in samples if s.confidence_band == band]
        if not group:
            continue
        out.append(
            BandPerformance(
                band=band,
                n=len(group),
                accuracy=round(accuracy(group), 4),
                brier=round(brier_score(group), 4),
            )
        )
    return out


def evaluate(samples: list[BacktestSample]) -> PerformanceReport:
    """Calcula el reporte de desempeño completo, con baseline y calibración."""
    if not samples:
        return PerformanceReport(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [], [])

    base = _constant_prediction_samples(samples, _base_rates(samples))
    cal_bins, ece = calibration(samples)
    return PerformanceReport(
        n=len(samples),
        accuracy=round(accuracy(samples), 4),
        brier=round(brier_score(samples), 4),
        log_loss=round(log_loss(samples), 4),
        baseline_brier=round(brier_score(base), 4),
        baseline_log_loss=round(log_loss(base), 4),
        ece=round(ece, 4),
        calibration=cal_bins,
        by_band=_by_band(samples),
    )
