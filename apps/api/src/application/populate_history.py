"""Arma y persiste el historial de predicciones.

- Partidos FINALIZADOS: predicción point-in-time (del backtest) + resultado real.
- Partidos PRÓXIMOS: la predicción que muestra la app (sin resultado todavía).

Esto puebla el historial durable: el track record real del modelo + las predicciones
abiertas que se resolverán cuando se jueguen los partidos.
"""

from __future__ import annotations

from ..domain.catalog import MatchStatus, Sport
from .backtest_service import BacktestService
from .catalog_ports import CatalogRepository, MatchQuery
from .prediction_history import MatchPredictionRecord, PredictionHistoryRepository
from .prediction_service import PredictionService, PredictionUnavailable

_ALL = 1_000_000


def collect_records(
    catalog: CatalogRepository,
    backtest: BacktestService,
    prediction: PredictionService,
) -> list[MatchPredictionRecord]:
    records: list[MatchPredictionRecord] = list(backtest.records())  # finalizados + resultado

    scheduled, _ = catalog.search_matches(
        MatchQuery(sport=Sport.SOCCER, status=MatchStatus.SCHEDULED, limit=_ALL)
    )
    for match in scheduled:
        try:
            pred = prediction.predict_for_match(match)
        except PredictionUnavailable:
            continue
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
            )
        )
    return records


def populate(
    catalog: CatalogRepository,
    backtest: BacktestService,
    prediction: PredictionService,
    history: PredictionHistoryRepository,
) -> int:
    """Guarda el historial si aún está vacío. Devuelve cuántas predicciones guardó."""
    if history.count() > 0:
        return 0
    return history.store_many(collect_records(catalog, backtest, prediction))
