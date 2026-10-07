"""Pruebas del modelo Dixon-Coles (requiere numpy/scipy del extra [pipeline])."""

import pathlib
import sys
import unittest
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("numpy/scipy no disponibles (extra [pipeline])") from None

from sports_predictor_ml.models.soccer.dixon_coles import (  # noqa: E402
    DixonColesModel,
    MatchObservation,
)


def _obs(home, away, hg, ag, day):
    return MatchObservation(home, away, hg, ag, datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=day))


class TestDixonColes(unittest.TestCase):
    def _trained(self) -> DixonColesModel:
        # 'strong' golea; 'weak' encaja. Datos sintéticos repetidos para señal clara.
        matches = []
        day = 0
        for _ in range(12):
            matches += [
                _obs("strong", "weak", 3, 0, day),
                _obs("strong", "mid", 2, 1, day + 1),
                _obs("mid", "weak", 2, 0, day + 2),
                _obs("weak", "mid", 0, 1, day + 3),
            ]
            day += 4
        return DixonColesModel(half_life_days=None).fit(matches)

    def test_probabilities_sum_to_one(self) -> None:
        p = self._trained().predict("strong", "weak")
        self.assertAlmostEqual(p.prob_home + p.prob_draw + p.prob_away, 1.0, places=3)

    def test_stronger_team_favored(self) -> None:
        p = self._trained().predict("strong", "weak")
        self.assertGreater(p.prob_home, p.prob_away)
        self.assertGreater(p.exp_home_goals, p.exp_away_goals)

    def test_markets_in_unit_interval(self) -> None:
        p = self._trained().predict("strong", "weak")
        # Una línea por cada umbral, con p_over en [0,1] y monótona decreciente.
        self.assertEqual(len(p.over_under), 5)
        overs = [po for _, po in p.over_under]
        for po in overs:
            self.assertGreaterEqual(po, 0.0)
            self.assertLessEqual(po, 1.0)
        self.assertTrue(all(a >= b for a, b in zip(overs, overs[1:])))  # Over baja con la línea
        self.assertGreaterEqual(p.prob_btts, 0.0)
        self.assertLessEqual(p.prob_btts, 1.0)

    def test_unknown_team_does_not_crash(self) -> None:
        p = self._trained().predict("unknown_a", "unknown_b")
        self.assertAlmostEqual(p.prob_home + p.prob_draw + p.prob_away, 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
