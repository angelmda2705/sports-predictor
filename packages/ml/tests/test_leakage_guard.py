"""Pruebas del guardián anti-fuga temporal."""

import pathlib
import sys
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sports_predictor_ml.features.leakage_guard import (  # noqa: E402
    LeakageError,
    assert_as_of,
    filter_historical,
)


@dataclass
class _Match:
    kickoff_utc: datetime


class TestAssertAsOf(unittest.TestCase):
    def setUp(self) -> None:
        self.kickoff = datetime(2025, 8, 16, 14, 0, tzinfo=UTC)

    def test_passes_when_observed_before_kickoff(self) -> None:
        observed = self.kickoff - timedelta(hours=1)
        assert_as_of(observed, self.kickoff, label="lesión")  # no debe lanzar

    def test_raises_when_observed_at_kickoff(self) -> None:
        with self.assertRaises(LeakageError):
            assert_as_of(self.kickoff, self.kickoff, label="dato")

    def test_raises_when_observed_after_kickoff(self) -> None:
        observed = self.kickoff + timedelta(minutes=1)
        with self.assertRaises(LeakageError):
            assert_as_of(observed, self.kickoff)

    def test_rejects_naive_vs_aware(self) -> None:
        naive = datetime(2025, 8, 16, 12, 0)
        with self.assertRaises(ValueError):
            assert_as_of(naive, self.kickoff)


class TestFilterHistorical(unittest.TestCase):
    def test_excludes_self_and_future(self) -> None:
        kickoff = datetime(2025, 8, 16, 14, 0, tzinfo=UTC)
        past = _Match(kickoff - timedelta(days=7))
        same = _Match(kickoff)  # el propio partido
        future = _Match(kickoff + timedelta(days=7))

        result = filter_historical([past, same, future], kickoff)

        self.assertIn(past, result)
        self.assertNotIn(same, result)
        self.assertNotIn(future, result)
        self.assertEqual(len(result), 1)

    def test_empty_when_no_history(self) -> None:
        kickoff = datetime(2025, 8, 16, 14, 0, tzinfo=UTC)
        future = _Match(kickoff + timedelta(days=1))
        self.assertEqual(filter_historical([future], kickoff), [])


if __name__ == "__main__":
    unittest.main()
