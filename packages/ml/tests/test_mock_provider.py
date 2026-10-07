"""Pruebas del proveedor mock: TODO dato debe venir etiquetado is_mock=True."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sports_predictor_ml.ingestion.providers.base import SportsDataProvider  # noqa: E402
from sports_predictor_ml.ingestion.providers.mock_provider import (  # noqa: E402
    MockSportsDataProvider,
)


class TestMockProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = MockSportsDataProvider(seed=42)

    def test_satisfies_port(self) -> None:
        # El mock cumple el contrato del puerto (Protocol runtime-checkable).
        self.assertIsInstance(self.provider, SportsDataProvider)

    def test_metadata_marked_mock(self) -> None:
        meta = self.provider.metadata()
        self.assertTrue(meta.is_mock)
        self.assertFalse(meta.requires_api_key)

    def test_all_teams_marked_mock(self) -> None:
        teams = self.provider.fetch_teams("ENG_PL", "2025-2026")
        self.assertGreater(len(teams), 0)
        self.assertTrue(all(t.is_mock for t in teams))

    def test_all_matches_marked_mock(self) -> None:
        matches = self.provider.fetch_matches("ENG_PL", "2025-2026")
        self.assertGreater(len(matches), 0)
        self.assertTrue(all(m.is_mock for m in matches))

    def test_finished_matches_have_scores_scheduled_do_not(self) -> None:
        matches = self.provider.fetch_matches("ENG_PL", "2025-2026")
        for m in matches:
            if m.status == "finished":
                self.assertIsNotNone(m.home_score)
                self.assertIsNotNone(m.away_score)
            elif m.status == "scheduled":
                self.assertIsNone(m.home_score)
                self.assertIsNone(m.away_score)

    def test_deterministic_with_same_seed(self) -> None:
        a = MockSportsDataProvider(seed=7).fetch_matches("ENG_PL", "2025-2026")
        b = MockSportsDataProvider(seed=7).fetch_matches("ENG_PL", "2025-2026")
        self.assertEqual(
            [(m.provider_ref, m.home_score, m.away_score) for m in a],
            [(m.provider_ref, m.home_score, m.away_score) for m in b],
        )

    def test_injuries_marked_mock(self) -> None:
        injuries = self.provider.fetch_injuries("ENG_PL", "2025-2026")
        self.assertTrue(all(i.is_mock for i in injuries))


if __name__ == "__main__":
    unittest.main()
