"""Predictor Dixon-Coles: envuelve el modelo de goles en una predicción presentable.

Produce la MISMA estructura que el predictor Elo (MatchPrediction) para que la API
y la UI no cambien, y además rellena los mercados derivados (Over/Under 2.5, BTTS)
que el Elo no puede dar. Reutiliza el criterio de confianza compartido.
"""

from __future__ import annotations

from ..models.soccer.dixon_coles import DixonColesModel, MatchObservation
from .soccer_baseline import (
    _BAND_HIGH,
    _BAND_MEDIUM,
    _MIN_MATCHES_FOR_FULL_QUALITY,
    MatchPrediction,
    MatchResult,
    OverUnderLine,
    PredictionFactor,
    _decisiveness,
)

MODEL_NAME = "soccer_dixon_coles"
MODEL_VERSION = "0.1.0"


class SoccerDixonColesPredictor:
    def __init__(self, *, half_life_days: float | None = 180.0) -> None:
        self._model = DixonColesModel(half_life_days=half_life_days)
        self._counts: dict[str, int] = {}

    def fit(self, history: list[MatchResult]) -> SoccerDixonColesPredictor:
        self._model.fit(
            [
                MatchObservation(r.home_code, r.away_code, r.home_goals, r.away_goals, r.kickoff)
                for r in history
            ]
        )
        for r in history:
            self._counts[r.home_code] = self._counts.get(r.home_code, 0) + 1
            self._counts[r.away_code] = self._counts.get(r.away_code, 0) + 1
        return self

    def predict(
        self,
        home_code: str,
        away_code: str,
        *,
        home_name: str | None = None,
        away_name: str | None = None,
    ) -> MatchPrediction:
        home_name = home_name or home_code
        away_name = away_name or away_code
        dc = self._model.predict(home_code, away_code)

        decisiveness = _decisiveness(dc.prob_home, dc.prob_draw, dc.prob_away)
        n_home = self._counts.get(home_code, 0)
        n_away = self._counts.get(away_code, 0)
        data_quality = min(1.0, (n_home + n_away) / _MIN_MATCHES_FOR_FULL_QUALITY)
        confidence = round(decisiveness * (0.4 + 0.6 * data_quality), 3)
        band = (
            "alta" if confidence >= _BAND_HIGH else "media" if confidence >= _BAND_MEDIUM else "baja"
        )

        return MatchPrediction(
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            prob_home=dc.prob_home,
            prob_draw=dc.prob_draw,
            prob_away=dc.prob_away,
            exp_home_goals=dc.exp_home_goals,
            exp_away_goals=dc.exp_away_goals,
            likely_scoreline=dc.likely_scoreline,
            confidence=confidence,
            confidence_band=band,
            decisiveness=round(decisiveness, 4),
            data_quality=round(data_quality, 4),
            rating_home=0.0,  # Dixon-Coles no usa Elo; la fuerza va en los factores.
            rating_away=0.0,
            n_history_home=n_home,
            n_history_away=n_away,
            factors=self._factors(home_code, away_code, home_name, away_name),
            over_under=[
                OverUnderLine(line=line, prob_over=p_over, prob_under=round(1.0 - p_over, 4))
                for line, p_over in dc.over_under
            ],
            prob_btts=dc.prob_btts,
        )

    def _factors(
        self, home_code: str, away_code: str, home_name: str, away_name: str
    ) -> list[PredictionFactor]:
        atk_h, def_h = self._model.strength(home_code)
        atk_a, def_a = self._model.strength(away_code)
        factors: list[PredictionFactor] = []

        # Ataque: índice mayor = más capacidad goleadora.
        if abs(atk_h - atk_a) > 0.05:
            favors = "home" if atk_h > atk_a else "away"
            stronger = home_name if atk_h > atk_a else away_name
            factors.append(
                PredictionFactor(
                    "Fortaleza ofensiva",
                    favors,
                    f"Mayor capacidad goleadora de {stronger} (índices {atk_h:+.2f} vs {atk_a:+.2f}).",
                )
            )
        # Defensa: índice menor = defensa más sólida (concede menos).
        if abs(def_h - def_a) > 0.05:
            favors = "home" if def_h < def_a else "away"
            solid = home_name if def_h < def_a else away_name
            factors.append(
                PredictionFactor(
                    "Solidez defensiva",
                    favors,
                    f"Defensa más sólida de {solid} (índices {def_h:+.2f} vs {def_a:+.2f}).",
                )
            )
        factors.append(
            PredictionFactor(
                "Ventaja de localía",
                "home",
                f"Se aplica ventaja de local (factor {self._model.home_advantage:+.2f}).",
            )
        )
        return factors
