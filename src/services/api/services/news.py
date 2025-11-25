"""资讯服务骨架，聚合结构化资讯/社媒信号。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from src.services.api.schemas.news import NewsItem, NewsResponse
from src.shared.config import Settings


class NewsService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._config = settings.service.news_service

    def fetch_latest(self, entity_id: str, entity_type: str, window_hours: int | None = None) -> NewsResponse:
        window = window_hours or self._config.get("default_window_hours", 48)
        now = datetime.now(timezone.utc)
        items: List[NewsItem] = [
            NewsItem(
                news_id=f"{entity_id}-news-1",
                entity_id=entity_id,
                entity_type=entity_type,
                title="主力前锋训练中恢复，可能出战",
                summary="球队医务组表示主力前锋恢复顺利，预计可在下一场比赛复出。",
                sentiment="positive",
                reliability_score=0.82,
                published_at=now - timedelta(hours=2),
                source="Official Club",
            ),
            NewsItem(
                news_id=f"{entity_id}-news-2",
                entity_id=entity_id,
                entity_type=entity_type,
                title="客队防线存在隐患",
                summary="上一轮联赛客队出现多次防守失误，教练组强调需要提升注意力。",
                sentiment="negative",
                reliability_score=0.61,
                published_at=now - timedelta(hours=6),
                source="SportsDaily",
            ),
        ]
        max_items = self._config.get("max_items", 10)
        return NewsResponse(window_hours=window, items=items[:max_items])
