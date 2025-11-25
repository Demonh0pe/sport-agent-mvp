from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.services.api.dependencies import get_prediction_service
from src.services.api.schemas.prediction import PredictionResponse
from src.services.api.services.prediction import PredictionService

router = APIRouter(tags=["prediction"])


@router.get("/{match_id}", response_model=PredictionResponse)
def get_prediction(
    match_id: str,
    phase: str | None = Query(default=None, description="预测时点，如 T-24h"),
    explain: bool = Query(default=False, description="是否附带解释信息"),
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    return service.get_prediction(match_id=match_id, phase=phase, explain=explain)


@router.get("/{match_id}/explain", response_model=PredictionResponse)
def get_prediction_with_explain(
    match_id: str,
    phase: str | None = Query(default=None),
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    return service.get_prediction(match_id=match_id, phase=phase, explain=True)
