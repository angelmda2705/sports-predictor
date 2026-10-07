"""Predictor baseline de fútbol soccer sobre el modelo Elo.

Convierte el rating Elo (ajustado replayando resultados pasados) en una predicción
presentable: probabilidades 1X2, goles esperados, marcador probable, nivel de
confianza con criterio matemático explícito, y factores explicativos.

⚠️ Es un BASELINE. Los goles esperados usan un supuesto simple documentado (no un
Poisson ajustado a datos). La confianza es provisional y debe **recalibrarse**
contra datos reales (curva de calibración) antes de tomarse como definitiva.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..models.soccer.elo import EloConfig, EloModel

MODEL_NAME = "soccer_elo_baseline"
MODEL_VERSION = "0.1.0"

# Supuesto baseline (NO ajustado a datos): total de goles promedio por partido,
# usado para repartir los goles esperados según la cuota de fuerza del Elo.
LEAGUE_AVG_TOTAL_GOALS = 2.6

# Partidos previos (sumando ambos equipos) para considerar "datos suficientes".
_MIN_MATCHES_FOR_FULL_QUALITY = 8

# Umbrales PROVISIONALES de banda de confianza (a recalibrar con datos reales).
_BAND_HIGH = 0.30
_BAND_MEDIUM = 0.12


@dataclass(frozen=True)
class MatchResult:
    """Resultado histórico usado para ajustar el Elo (debe ser anterior al fixture)."""

    home_code: str
    away_code: str
    kickoff: datetime
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class PredictionFactor:
    label: str
    favors: str  # 'home' | 'away' | 'none'
    detail: str


@dataclass(frozen=True)
class OverUnderLine:
    line: float
    prob_over: float
    prob_under: float


@dataclass(frozen=True)
class ContextNote:
    """Riesgo contextual no capturado por el modelo (p. ej. equipo ya clasificado)."""

    kind: str  # 'clinched_qualification' | ...
    team: str
    message: str


@dataclass(frozen=True)
class MatchPrediction:
    model_name: str
    model_version: str
    prob_home: float
    prob_draw: float
    prob_away: float
    exp_home_goals: float
    exp_away_goals: float
    likely_scoreline: str
    confidence: float
    confidence_band: str  # 'baja' | 'media' | 'alta'
    decisiveness: float
    data_quality: float
    rating_home: float
    rating_away: float
    n_history_home: int
    n_history_away: int
    factors: list[PredictionFactor]
    # Mercados derivados (solo Dixon-Coles, que modela goles). None en Elo.
    over_under: list[OverUnderLine] | None = None
    prob_btts: float | None = None
    # Riesgos contextuales (p. ej. selección ya clasificada que podría rotar).
    context: list[ContextNote] = field(default_factory=list)


def _decisiveness(p_home: float, p_draw: float, p_away: float) -> float:
    """Qué tan lopsidada está la predicción, en [0,1].

    Mide cuánto supera la probabilidad máxima al azar (1/3): 0 cuando es un
    triple empate (1/3,1/3,1/3) y 1 cuando un resultado es prácticamente seguro.
    Tiene un rango más útil que la entropía para distribuciones 1X2 reales.
    """
    top = max(p_home, p_draw, p_away)
    return max(0.0, min(1.0, (top - 1.0 / 3.0) / (2.0 / 3.0)))


class SoccerEloBaseline:
    """Ajusta Elo con el historial y predice un fixture."""

    def __init__(
        self,
        config: EloConfig | None = None,
        *,
        initial_ratings: dict[str, float] | None = None,
        initial_counts: dict[str, int] | None = None,
    ) -> None:
        self._config = config or EloConfig()
        self._model = EloModel(config=self._config)
        # Siembra de ratings reales (p. ej. Elo de selecciones desde historial
        # internacional) y de los conteos de partidos previos, para que la
        # confianza refleje la profundidad de datos real, no parta de cero.
        if initial_ratings:
            self._model.ratings = dict(initial_ratings)
        self._counts: dict[str, int] = dict(initial_counts) if initial_counts else {}

    def fit(self, history: list[MatchResult]) -> SoccerEloBaseline:
        """Replaya los resultados en orden cronológico para obtener los ratings."""
        for r in sorted(history, key=lambda m: m.kickoff):
            self._model.update(r.home_code, r.away_code, r.home_goals, r.away_goals)
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

        p_home, p_draw, p_away = self._model.match_probabilities(home_code, away_code)
        share = self._model.expected_score(home_code, away_code)
        exp_home = round(LEAGUE_AVG_TOTAL_GOALS * share, 1)
        exp_away = round(LEAGUE_AVG_TOTAL_GOALS * (1.0 - share), 1)
        likely = f"{round(LEAGUE_AVG_TOTAL_GOALS * share)}-{round(LEAGUE_AVG_TOTAL_GOALS * (1 - share))}"

        # Confianza = decisividad (qué tan lopsidada es la distribución) ajustada
        # por la cantidad de datos disponibles. Definición explícita (§8.1 del doc).
        decisiveness = _decisiveness(p_home, p_draw, p_away)
        n_home = self._counts.get(home_code, 0)
        n_away = self._counts.get(away_code, 0)
        data_quality = min(1.0, (n_home + n_away) / _MIN_MATCHES_FOR_FULL_QUALITY)
        confidence = round(decisiveness * (0.4 + 0.6 * data_quality), 3)
        band = (
            "alta" if confidence >= _BAND_HIGH else "media" if confidence >= _BAND_MEDIUM else "baja"
        )

        factors = self._build_factors(
            home_code, away_code, home_name, away_name, n_home, n_away
        )

        return MatchPrediction(
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            prob_home=round(p_home, 4),
            prob_draw=round(p_draw, 4),
            prob_away=round(p_away, 4),
            exp_home_goals=exp_home,
            exp_away_goals=exp_away,
            likely_scoreline=likely,
            confidence=confidence,
            confidence_band=band,
            decisiveness=round(decisiveness, 4),
            data_quality=round(data_quality, 4),
            rating_home=round(self._model.get_rating(home_code), 1),
            rating_away=round(self._model.get_rating(away_code), 1),
            n_history_home=n_home,
            n_history_away=n_away,
            factors=factors,
        )

    def _build_factors(
        self,
        home_code: str,
        away_code: str,
        home_name: str,
        away_name: str,
        n_home: int,
        n_away: int,
    ) -> list[PredictionFactor]:
        factors: list[PredictionFactor] = []

        r_home = self._model.get_rating(home_code)
        r_away = self._model.get_rating(away_code)
        gap = r_home - r_away
        if abs(gap) < 1.0:
            factors.append(
                PredictionFactor(
                    "Nivel parejo",
                    "none",
                    f"Ratings Elo similares ({r_home:.0f} vs {r_away:.0f}).",
                )
            )
        else:
            favored_name = home_name if gap > 0 else away_name
            factors.append(
                PredictionFactor(
                    "Diferencia de Elo",
                    "home" if gap > 0 else "away",
                    f"Elo {home_name} {r_home:.0f} vs {away_name} {r_away:.0f}: "
                    f"favorece a {favored_name}.",
                )
            )

        factors.append(
            PredictionFactor(
                "Ventaja de localía",
                "home",
                f"Se aplica ventaja de local (+{self._config.home_advantage:.0f} Elo).",
            )
        )

        if (n_home + n_away) < _MIN_MATCHES_FOR_FULL_QUALITY:
            factors.append(
                PredictionFactor(
                    "Datos limitados",
                    "none",
                    f"Pocos partidos previos (local: {n_home}, visita: {n_away}); "
                    f"reduce la confianza.",
                )
            )

        return factors
