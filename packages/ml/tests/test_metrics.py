"""Pruebas de las métricas de evaluación 1X2."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sports_predictor_ml.evaluation.metrics import (  # noqa: E402
    BacktestSample,
    accuracy,
    brier_score,
    calibration,
    evaluate,
    log_loss,
)


def _s(ph, pd, pa, actual, band="media"):
    return BacktestSample(ph, pd, pa, actual, band, "TEST")


class TestMetrics(unittest.TestCase):
    def test_perfect_prediction_brier_zero(self) -> None:
        samples = [_s(1.0, 0.0, 0.0, "H"), _s(0.0, 0.0, 1.0, "A")]
        self.assertAlmostEqual(brier_score(samples), 0.0, places=9)

    def test_perfect_prediction_log_loss_near_zero(self) -> None:
        samples = [_s(1.0, 0.0, 0.0, "H")]
        self.assertAlmostEqual(log_loss(samples), 0.0, places=6)

    def test_brier_worst_case(self) -> None:
        # Predijo lo contrario con certeza: Σ(p-y)² = (0-1)²+(1-0)² = 2 por muestra.
        samples = [_s(0.0, 0.0, 1.0, "H")]
        self.assertAlmostEqual(brier_score(samples), 2.0, places=9)

    def test_accuracy(self) -> None:
        samples = [_s(0.6, 0.2, 0.2, "H"), _s(0.2, 0.2, 0.6, "H")]
        self.assertAlmostEqual(accuracy(samples), 0.5, places=9)

    def test_empty_is_safe(self) -> None:
        report = evaluate([])
        self.assertEqual(report.n, 0)
        self.assertEqual(report.calibration, [])

    def test_evaluate_includes_baseline_and_calibration(self) -> None:
        samples = [
            _s(0.5, 0.3, 0.2, "H"),
            _s(0.4, 0.3, 0.3, "D"),
            _s(0.3, 0.3, 0.4, "A"),
            _s(0.5, 0.25, 0.25, "H"),
        ]
        report = evaluate(samples)
        self.assertEqual(report.n, 4)
        self.assertGreaterEqual(report.brier, 0.0)
        self.assertGreaterEqual(report.baseline_brier, 0.0)
        self.assertGreaterEqual(report.ece, 0.0)
        # La suma de conteos de los bins de calibración = 3 puntos por muestra.
        self.assertEqual(sum(b.count for b in report.calibration), 3 * 4)

    def test_calibration_perfectly_calibrated_low_ece(self) -> None:
        # Predicciones uniformes 1/3 con resultados balanceados → ECE bajo.
        samples = [
            _s(1 / 3, 1 / 3, 1 / 3, "H"),
            _s(1 / 3, 1 / 3, 1 / 3, "D"),
            _s(1 / 3, 1 / 3, 1 / 3, "A"),
        ]
        _, ece = calibration(samples)
        self.assertLess(ece, 0.1)


if __name__ == "__main__":
    unittest.main()
