from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.services.api.dependencies import get_news_service
from src.services.api.schemas.news import NewsResponse
from src.services.api.services.news import NewsService

router = APIRouter(tags=["news"])


@router.get("/")
def get_news(
    entity_id: str = Query(..., description="实体ID，可为球队/比赛/球员"),
    entity_type: str = Query("team", regex="^(team|match|player)$"),
    window_hours: int | None = Query(default=None),
    service: NewsService = Depends(get_news_service),
) -> NewsResponse:
    return service.fetch_latest(entity_id=entity_id, entity_type=entity_type, window_hours=window_hours)
