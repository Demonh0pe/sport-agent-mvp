"""资讯/社媒相关的 API Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    news_id: str
    entity_id: str
    entity_type: Literal["team", "match", "player"]
    title: str
    summary: str
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"
    reliability_score: float = Field(..., ge=0.0, le=1.0)
    published_at: datetime
    source: str


class NewsResponse(BaseModel):
    window_hours: int
    items: List[NewsItem] = Field(default_factory=list)
