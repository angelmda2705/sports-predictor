"""Endpoint de predicción de un partido."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...application.catalog_service import CatalogService
from ...application.prediction_service import PredictionService, PredictionUnavailable
from ..deps import get_catalog_service, get_prediction_service
from ..schemas_prediction import PredictionResponse

router = APIRouter(tags=["prediction"])


@router.get("/matches/{match_id}/prediction", response_model=PredictionResponse)
def get_prediction(
    match_id: int,
    catalog: CatalogService = Depends(get_catalog_service),
    predictor: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    match = catalog.get_match(match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Partido no encontrado.")
    try:
        prediction = predictor.predict_for_match(match)
    except PredictionUnavailable as exc:
        # 422: el partido existe pero no hay modelo aplicable todavía.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return PredictionResponse.from_ml(match_id, prediction, is_mock=match.is_mock)
