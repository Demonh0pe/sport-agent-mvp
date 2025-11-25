"""预测服务相关的 Pydantic Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ProbabilityBreakdown(BaseModel):
    home_win: float = Field(..., ge=0.0, le=1.0)
    draw: float = Field(..., ge=0.0, le=1.0)
    away_win: float = Field(..., ge=0.0, le=1.0)


class ExplanationFactor(BaseModel):
    name: str
    value: float | str
    impact: Literal["positive", "negative", "neutral"] = "neutral"
    comment: str


class PredictionExplanation(BaseModel):
    summary: str
    factors: List[ExplanationFactor] = Field(default_factory=list)


class PredictionResponse(BaseModel):
    match_id: str
    phase: str = "T-24h"
    model_version: str
    generated_at: datetime
    probabilities: ProbabilityBreakdown
    cold_start: bool = False
    uncertainty_flag: bool = False
    explanation: Optional[PredictionExplanation] = None
