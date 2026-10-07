"""Servicio de predicción.

Orquesta: toma un partido, recupera su historial (resultados previos de la misma
competición, **anteriores al kickoff** para no filtrar información) y ejecuta el
predictor baseline de `packages/ml`. No implementa el modelo aquí: lo reutiliza.
"""

from __future__ import annotations

from dataclasses import replace

from sports_predictor_ml.prediction.soccer_baseline import (
    _BAND_HIGH,
    _BAND_MEDIUM,
    MatchPrediction,
    MatchResult,
    PredictionFactor,
    SoccerEloBaseline,
)
from sports_predictor_ml.prediction.soccer_dixon_coles import SoccerDixonColesPredictor

from ..domain.catalog import Match, MatchStatus, Sport
from .catalog_ports import CatalogRepository, MatchQuery
from .stakes import StakesAnalyzer

# Las predicciones y el backtest leen del repositorio (cómputo interno), no del
# servicio de UI, para no toparse con el tope de paginación de las vistas.
_ALL = 1_000_000

# Dixon-Coles necesita suficientes goles para estimar ataque/defensa por equipo.
# Con menos partidos (p. ej. datos mock) se cae al baseline Elo.
_DC_MIN_MATCHES = 200


class PredictionUnavailable(Exception):
    """No hay predictor disponible para este partido (p. ej. deporte no soportado)."""


class PredictionService:
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
        # Caché de modelos Dixon-Coles ya ajustados, por competición (ligas reales).
        self._dc_cache: dict[str, SoccerDixonColesPredictor] = {}
        # Caché del analizador de stakes (clasificación) por competición de selecciones.
        self._stakes_cache: dict[str, StakesAnalyzer] = {}

    def predict_for_match(self, match: Match) -> MatchPrediction:
        if match.sport != Sport.SOCCER:
            raise PredictionUnavailable(
                "El modelo baseline actual solo cubre fútbol soccer. "
                "El fútbol americano llega en un incremento posterior."
            )

        history_items, _ = self._catalog.search_matches(
            MatchQuery(
                competition_code=match.competition_code,
                status=MatchStatus.FINISHED,
                limit=_ALL,
            )
        )

        all_results = [
            MatchResult(
                home_code=m.home_team.code,
                away_code=m.away_team.code,
                kickoff=m.kickoff_utc,
                home_goals=m.home_score,
                away_goals=m.away_score,
            )
            for m in history_items
            if m.home_score is not None and m.away_score is not None
        ]
        is_intl = match.competition_code in self._international

        # Ligas reales con suficientes goles → Dixon-Coles (mejor calibrado).
        if not is_intl and len(all_results) >= _DC_MIN_MATCHES:
            return self._dixon_coles(match, all_results).predict(
                match.home_team.code,
                match.away_team.code,
                home_name=match.home_team.name,
                away_name=match.away_team.name,
            )

        # Selecciones (Elo sembrado con historial internacional real) o datos escasos.
        # Anti-fuga: solo resultados ANTERIORES al kickoff del partido a predecir.
        results = [r for r in all_results if r.kickoff < match.kickoff_utc]
        baseline = SoccerEloBaseline(
            initial_ratings=self._seed_ratings if is_intl else None,
            initial_counts=self._seed_counts if is_intl else None,
        ).fit(results)
        prediction = baseline.predict(
            match.home_team.code,
            match.away_team.code,
            home_name=match.home_team.name,
            away_name=match.away_team.name,
        )
        # Contexto de torneo: si una selección ya clasificó, advertir y bajar confianza.
        if is_intl:
            prediction = self._apply_stakes(match, prediction)
        return prediction

    def _apply_stakes(self, match: Match, prediction: MatchPrediction) -> MatchPrediction:
        analyzer = self._stakes_cache.get(match.competition_code)
        if analyzer is None:
            comp_matches, _ = self._catalog.search_matches(
                MatchQuery(competition_code=match.competition_code, limit=_ALL)
            )
            analyzer = StakesAnalyzer(comp_matches)
            self._stakes_cache[match.competition_code] = analyzer

        notes = analyzer.context_for(match)
        if not notes:
            return prediction

        # Menor incentivo → más incertidumbre: se reduce la confianza.
        new_confidence = round(prediction.confidence * (0.6 ** len(notes)), 3)
        new_band = (
            "alta"
            if new_confidence >= _BAND_HIGH
            else "media"
            if new_confidence >= _BAND_MEDIUM
            else "baja"
        )
        extra_factors = [
            PredictionFactor("Contexto: incentivo reducido", "none", n.message) for n in notes
        ]
        return replace(
            prediction,
            confidence=new_confidence,
            confidence_band=new_band,
            factors=prediction.factors + extra_factors,
            context=notes,
        )

    def _dixon_coles(
        self, match: Match, all_results: list[MatchResult]
    ) -> SoccerDixonColesPredictor:
        """Modelo Dixon-Coles cacheado por competición (ajuste único reutilizable)."""
        cached = self._dc_cache.get(match.competition_code)
        if cached is None:
            cached = SoccerDixonColesPredictor().fit(all_results)
            self._dc_cache[match.competition_code] = cached
        return cached
