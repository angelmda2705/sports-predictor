"""Schemas de respuesta de predicción."""

from __future__ import annotations

from pydantic import BaseModel

from sports_predictor_ml.prediction.soccer_baseline import MatchPrediction

_CONFIDENCE_CRITERION = (
    "confianza = decisividad (cuánto supera la probabilidad máxima al azar 1/3) "
    "ajustada por la disponibilidad de datos (partidos previos). Umbrales de banda "
    "provisionales (alta ≥ 0.30, media ≥ 0.12), a recalibrar con datos reales."
)


class ModelInfo(BaseModel):
    name: str
    version: str


class Probabilities(BaseModel):
    home: float
    draw: float
    away: float


class ExpectedGoals(BaseModel):
    home: float
    away: float


class Confidence(BaseModel):
    score: float
    band: str  # baja | media | alta
    decisiveness: float
    data_quality: float
    criterion: str


class Ratings(BaseModel):
    home: float
    away: float


class HistoryCounts(BaseModel):
    home: int
    away: int


class FactorResponse(BaseModel):
    label: str
    favors: str  # home | away | none
    detail: str


class ContextResponse(BaseModel):
    kind: str
    team: str
    message: str


class OverUnderResponse(BaseModel):
    line: float
    over: float
    under: float


class Markets(BaseModel):
    over_under: list[OverUnderResponse]  # P(más de / menos de) por línea de goles
    btts: float | None  # P(ambos equipos anotan)


class PredictionResponse(BaseModel):
    match_id: int
    model: ModelInfo
    probabilities: Probabilities
    expected_goals: ExpectedGoals
    likely_scoreline: str
    markets: Markets
    confidence: Confidence
    ratings: Ratings
    history_counts: HistoryCounts
    factors: list[FactorResponse]
    context: list[ContextResponse]
    is_mock: bool
    disclaimer: str

    @classmethod
    def from_ml(cls, match_id: int, p: MatchPrediction, *, is_mock: bool) -> PredictionResponse:
        disclaimer = (
            "Estimación probabilística, no una certeza. "
            + ("Basada en DATOS MOCK de demostración. " if is_mock else "")
            + f"Modelo: {p.model_name}; no garantiza resultados."
        )
        return cls(
            match_id=match_id,
            model=ModelInfo(name=p.model_name, version=p.model_version),
            probabilities=Probabilities(home=p.prob_home, draw=p.prob_draw, away=p.prob_away),
            expected_goals=ExpectedGoals(home=p.exp_home_goals, away=p.exp_away_goals),
            likely_scoreline=p.likely_scoreline,
            markets=Markets(
                over_under=[
                    OverUnderResponse(line=ou.line, over=ou.prob_over, under=ou.prob_under)
                    for ou in (p.over_under or [])
                ],
                btts=p.prob_btts,
            ),
            confidence=Confidence(
                score=p.confidence,
                band=p.confidence_band,
                decisiveness=p.decisiveness,
                data_quality=p.data_quality,
                criterion=_CONFIDENCE_CRITERION,
            ),
            ratings=Ratings(home=p.rating_home, away=p.rating_away),
            history_counts=HistoryCounts(home=p.n_history_home, away=p.n_history_away),
            factors=[
                FactorResponse(label=f.label, favors=f.favors, detail=f.detail) for f in p.factors
            ],
            context=[
                ContextResponse(kind=c.kind, team=c.team, message=c.message) for c in p.context
            ],
            is_mock=is_mock,
            disclaimer=disclaimer,
        )
