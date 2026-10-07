"""Endpoint del dashboard de rendimiento del modelo (transparencia)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...application.backtest_service import BacktestService
from ..deps import get_backtest_service
from ..schemas_performance import PerformanceResponse

router = APIRouter(tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse)
def get_performance(
    competition: str | None = Query(default=None, description="Filtra por competición"),
    backtest: BacktestService = Depends(get_backtest_service),
) -> PerformanceResponse:
    report, contains_mock = backtest.run(competition_code=competition)
    return PerformanceResponse.from_report(report, is_mock=contains_mock)
