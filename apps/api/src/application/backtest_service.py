"""Servicio de backtesting walk-forward del modelo baseline.

Para cada partido de soccer ya finalizado, predice usando SOLO el historial
anterior a su kickoff (anti-fuga), compara contra el resultado real y agrega las
métricas. Es la base del dashboard de transparencia: muestra el desempeño honesto
del modelo, incluidos sus fallos.

⚠️ Corre sobre datos mock mientras no haya proveedor real; el reporte lo etiqueta.
"""

from __future__ import annotations

from sports_predictor_ml.evaluation.metrics import (
    BacktestSample,
    PerformanceReport,
    evaluate,
)
from sports_predictor_ml.prediction.soccer_baseline import (
    MatchResult,
    SoccerEloBaseline,
)

from ..domain.catalog import Match, MatchStatus, Sport
from .catalog_ports import CatalogRepository, MatchQuery
from .prediction_history import MatchPredictionRecord

# Backtest = cómputo interno: lee del repositorio sin tope de paginación.
_ALL = 1_000_000


def _outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if home_score == away_score:
        return "D"
    return "A"


class BacktestService:
    def __init__(
        self,
        catalog: CatalogRepository,
        *,
        seed_ratings: dict[str, float] | None = None,
        seed_counts: dict[str, int] | None = None,
        international_competitions: set[str] | None = None,
    ) -> None:
        self._catalog = catalog
        self._seed_ratings = seed_ratings or {}
        self._seed_counts = seed_counts or {}
        self._international = international_competitions or set()

    def run(self, *, competition_code: str | None = None) -> tuple[PerformanceReport, bool]:
        """Devuelve ``(reporte, contiene_mock)`` del backtest de soccer."""
        recs = self.records(competition_code=competition_code)
        samples = [
            BacktestSample(
                r.prob_home, r.prob_draw, r.prob_away, r.actual,  # type: ignore[arg-type]
                r.confidence_band, r.competition_code,
            )
            for r in recs
        ]
        return evaluate(samples), any(r.is_mock for r in recs)

    def records(self, *, competition_code: str | None = None) -> list[MatchPredictionRecord]:
        """Predicciones point-in-time (con resultado) de cada partido FINALIZADO.

        Walk-forward de un solo paso por competición (O(n)): para cada partido se
        predice con el estado del modelo ANTES del partido y luego se actualiza.
        Los resultados con el MISMO kickoff no se informan entre sí (anti-fuga
        estricto): las actualizaciones se difieren hasta avanzar de fecha.
        """
        finished, _ = self._catalog.search_matches(
            MatchQuery(
                sport=Sport.SOCCER,
                competition_code=competition_code,
                status=MatchStatus.FINISHED,
                limit=_ALL,
            )
        )
        finished = [m for m in finished if m.home_score is not None and m.away_score is not None]

        by_competition: dict[str, list[Match]] = {}
        for match in finished:
            by_competition.setdefault(match.competition_code, []).append(match)

        records: list[MatchPredictionRecord] = []
        for comp_code, comp_matches in by_competition.items():
            comp_matches.sort(key=lambda m: m.kickoff_utc)
            is_intl = comp_code in self._international
            baseline = SoccerEloBaseline(
                initial_ratings=self._seed_ratings if is_intl else None,
                initial_counts=self._seed_counts if is_intl else None,
            )
            pending: list[MatchResult] = []
            current_kickoff = None
            for match in comp_matches:
                if current_kickoff is not None and match.kickoff_utc > current_kickoff:
                    baseline.fit(pending)
                    pending = []
                current_kickoff = match.kickoff_utc

                pred = baseline.predict(
                    match.home_team.code,
                    match.away_team.code,
                    home_name=match.home_team.name,
                    away_name=match.away_team.name,
                )
                assert match.home_score is not None and match.away_score is not None
                records.append(
                    MatchPredictionRecord(
                        match_id=match.id,
                        competition_code=match.competition_code,
                        home_name=match.home_team.name,
                        away_name=match.away_team.name,
                        kickoff=match.kickoff_utc,
                        prob_home=pred.prob_home,
                        prob_draw=pred.prob_draw,
                        prob_away=pred.prob_away,
                        confidence=pred.confidence,
                        confidence_band=pred.confidence_band,
                        model_name=pred.model_name,
                        model_version=pred.model_version,
                        is_mock=match.is_mock,
                        actual=_outcome(match.home_score, match.away_score),
                        home_score=match.home_score,
                        away_score=match.away_score,
                    )
                )
                pending.append(
                    MatchResult(
                        home_code=match.home_team.code,
                        away_code=match.away_team.code,
                        kickoff=match.kickoff_utc,
                        home_goals=match.home_score,
                        away_goals=match.away_score,
                    )
                )

        return records
