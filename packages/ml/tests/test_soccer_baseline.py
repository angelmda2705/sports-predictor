"""Pruebas del predictor baseline de soccer (Elo)."""

import pathlib
import sys
import unittest
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sports_predictor_ml.prediction.soccer_baseline import (  # noqa: E402
    MODEL_NAME,
    MatchResult,
    SoccerEloBaseline,
)


def _result(home, away, hg, ag, day):
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return MatchResult(home, away, base + timedelta(days=day), hg, ag)


class TestSoccerBaseline(unittest.TestCase):
    def test_probabilities_sum_to_one(self) -> None:
        pred = SoccerEloBaseline().fit([]).predict("A", "B")
        total = pred.prob_home + pred.prob_draw + pred.prob_away
        self.assertAlmostEqual(total, 1.0, places=3)
        self.assertEqual(pred.model_name, MODEL_NAME)

    def test_no_history_means_low_confidence(self) -> None:
        # Sin historial: datos insuficientes => confianza baja y aviso de datos.
        pred = SoccerEloBaseline().fit([]).predict("A", "B")
        self.assertEqual(pred.data_quality, 0.0)
        self.assertEqual(pred.confidence_band, "baja")
        labels = {f.label for f in pred.factors}
        self.assertIn("Datos limitados", labels)

    def test_winning_team_is_favored(self) -> None:
        # 'Strong' golea a varios rivales; debe quedar favorito ante 'weak'.
        history = [
            _result("strong", "x", 3, 0, 1),
            _result("strong", "y", 2, 0, 2),
            _result("z", "strong", 0, 2, 3),
            _result("weak", "x", 0, 3, 1),
            _result("weak", "y", 0, 2, 2),
        ]
        pred = SoccerEloBaseline().fit(history).predict(
            "strong", "weak", home_name="Strong", away_name="Weak"
        )
        self.assertGreater(pred.prob_home, pred.prob_away)
        self.assertGreater(pred.rating_home, pred.rating_away)
        self.assertGreaterEqual(pred.exp_home_goals, pred.exp_away_goals)

    def test_history_increases_data_quality(self) -> None:
        history = [_result("A", "B", 1, 0, i) for i in range(5)]
        pred = SoccerEloBaseline().fit(history).predict("A", "B")
        self.assertGreater(pred.data_quality, 0.0)
        self.assertGreaterEqual(pred.n_history_home, 5)

    def test_confidence_in_unit_interval(self) -> None:
        history = [_result("A", "B", 2, 1, i) for i in range(4)]
        pred = SoccerEloBaseline().fit(history).predict("A", "B")
        self.assertGreaterEqual(pred.confidence, 0.0)
        self.assertLessEqual(pred.confidence, 1.0)
        self.assertIn(pred.confidence_band, {"baja", "media", "alta"})


if __name__ == "__main__":
    unittest.main()
