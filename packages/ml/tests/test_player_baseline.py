"""Pruebas del baseline de predicción individual de jugadores."""

import pathlib
import sys
import unittest
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sports_predictor_ml.players.baseline import PlayerGameLog, predict_player  # noqa: E402

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _g(day, started, minutes, goals=0, shots=0):
    return PlayerGameLog(
        kickoff=_BASE + timedelta(days=day),
        started=started,
        minutes=minutes,
        goals=goals,
        shots=shots,
        shots_on=min(shots, 1),
    )


class TestPlayerBaseline(unittest.TestCase):
    def test_no_history_is_unavailable(self) -> None:
        p = predict_player([])
        self.assertEqual(p.n_games, 0)
        self.assertIsNotNone(p.low_confidence_note)

    def test_regular_starter_high_minutes(self) -> None:
        logs = [_g(i, True, 90, goals=(1 if i % 2 else 0), shots=3) for i in range(10)]
        p = predict_player(logs)
        self.assertGreater(p.prob_start, 0.9)
        self.assertGreater(p.expected_minutes, 80)
        self.assertEqual(p.confidence_band, "alta")
        # ~0.5 goles/90 a 90 min → ~0.5 esperados → P(anota) ~0.39.
        self.assertGreater(p.expected_goals, 0.3)
        self.assertGreater(p.prob_scores, 0.0)
        self.assertLess(p.prob_scores, 1.0)

    def test_per90_scaling_by_minutes(self) -> None:
        # Anota 1 gol jugando 45 min en cada partido → 2 goles/90, pero si esperamos
        # ~45 min, los goles esperados deben rondar 1, no 2.
        logs = [_g(i, True, 45, goals=1, shots=2) for i in range(8)]
        p = predict_player(logs)
        self.assertLess(p.expected_minutes, 60)
        self.assertAlmostEqual(p.expected_goals, 1.0, delta=0.25)

    def test_fringe_player_low_confidence(self) -> None:
        logs = [_g(0, False, 10), _g(3, False, 8)]
        p = predict_player(logs)
        self.assertLess(p.prob_start, 0.5)
        self.assertEqual(p.confidence_band, "baja")
        self.assertIsNotNone(p.low_confidence_note)


if __name__ == "__main__":
    unittest.main()
