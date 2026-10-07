"""Pruebas del modelo Elo baseline (soccer)."""

import pathlib
import sys
import unittest

# Permite ejecutar con `python -m unittest` sin instalar el paquete.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sports_predictor_ml.models.soccer.elo import EloConfig, EloModel  # noqa: E402


class TestEloConfig(unittest.TestCase):
    def test_rejects_invalid_draw_max(self) -> None:
        with self.assertRaises(ValueError):
            EloConfig(draw_max=1.0)
        with self.assertRaises(ValueError):
            EloConfig(draw_max=-0.1)

    def test_rejects_non_positive_k(self) -> None:
        with self.assertRaises(ValueError):
            EloConfig(k=0)


class TestEloProbabilities(unittest.TestCase):
    def setUp(self) -> None:
        # Sin ventaja de localía para aislar el efecto del rating.
        self.model = EloModel(config=EloConfig(home_advantage=0.0))

    def test_equal_ratings_symmetric(self) -> None:
        p_home, p_draw, p_away = self.model.match_probabilities("A", "B")
        self.assertAlmostEqual(p_home, p_away, places=9)
        self.assertAlmostEqual(p_draw, self.model.config.draw_max, places=9)

    def test_probabilities_sum_to_one(self) -> None:
        for home_rating, away_rating in [(1500, 1500), (1800, 1500), (1400, 1900)]:
            self.model.ratings = {"H": float(home_rating), "A": float(away_rating)}
            probs = self.model.match_probabilities("H", "A")
            self.assertAlmostEqual(sum(probs), 1.0, places=9)
            for p in probs:
                self.assertGreaterEqual(p, 0.0)
                self.assertLessEqual(p, 1.0)

    def test_stronger_team_more_likely_to_win(self) -> None:
        self.model.ratings = {"strong": 1800.0, "weak": 1400.0}
        p_home, _, p_away = self.model.match_probabilities("strong", "weak")
        self.assertGreater(p_home, p_away)

    def test_home_advantage_increases_home_prob(self) -> None:
        no_adv = EloModel(config=EloConfig(home_advantage=0.0))
        with_adv = EloModel(config=EloConfig(home_advantage=100.0))
        p_home_no = no_adv.match_probabilities("A", "B")[0]
        p_home_yes = with_adv.match_probabilities("A", "B")[0]
        self.assertGreater(p_home_yes, p_home_no)

    def test_larger_gap_increases_favorite_prob(self) -> None:
        self.model.ratings = {"H": 1600.0, "A": 1500.0}
        small_gap = self.model.match_probabilities("H", "A")[0]
        self.model.ratings = {"H": 1900.0, "A": 1500.0}
        large_gap = self.model.match_probabilities("H", "A")[0]
        self.assertGreater(large_gap, small_gap)


class TestEloUpdate(unittest.TestCase):
    def test_winner_gains_loser_loses_zero_sum(self) -> None:
        model = EloModel(config=EloConfig(home_advantage=0.0))
        model.ratings = {"H": 1500.0, "A": 1500.0}
        new_home, new_away = model.update("H", "A", home_goals=2, away_goals=0)
        self.assertGreater(new_home, 1500.0)
        self.assertLess(new_away, 1500.0)
        # Suma cero: el total de rating se conserva.
        self.assertAlmostEqual(new_home + new_away, 3000.0, places=9)

    def test_unexpected_result_moves_rating_more(self) -> None:
        # El favorito que pierde cae más que lo que cae al perder un partido parejo.
        underdog_win = EloModel(config=EloConfig(home_advantage=0.0))
        underdog_win.ratings = {"fav": 1900.0, "dog": 1400.0}
        new_fav, _ = underdog_win.update("fav", "dog", 0, 1)
        drop_big_upset = 1900.0 - new_fav

        even = EloModel(config=EloConfig(home_advantage=0.0))
        even.ratings = {"fav": 1500.0, "dog": 1500.0}
        new_even, _ = even.update("fav", "dog", 0, 1)
        drop_even = 1500.0 - new_even

        self.assertGreater(drop_big_upset, drop_even)

    def test_draw_moves_lower_rated_up(self) -> None:
        model = EloModel(config=EloConfig(home_advantage=0.0))
        model.ratings = {"strong": 1800.0, "weak": 1400.0}
        new_strong, new_weak = model.update("strong", "weak", 1, 1)
        # Un empate es "mejor de lo esperado" para el débil.
        self.assertLess(new_strong, 1800.0)
        self.assertGreater(new_weak, 1400.0)


if __name__ == "__main__":
    unittest.main()
