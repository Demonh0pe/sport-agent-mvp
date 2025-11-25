"""Agent 工具的接口契约（输入/输出 Schema）。

这些定义将被 Planner/Executor 以及 LLM 提示引用，决定工具调用方式。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class MatchResolverToolInput(BaseModel):
    """从自然语言解析比赛 ID 的请求。"""

    query: str = Field(..., description="用户自然语言描述，如'曼联下一场比赛'。")
    league_hint: Optional[str] = Field(None, description="可选联赛提示，例如 'EPL'。")
    date_hint: Optional[str] = Field(
        None, description="可选日期提示，ISO 或 'next saturday' 等自然语言。"
    )


class MatchResolverToolOutput(BaseModel):
    """解析结果：比赛 ID 以及补充信息。"""

    match_id: str = Field(..., description="标准化后的比赛唯一 ID。")
    home_team_id: Optional[str] = Field(None, description="主队 ID，用于后续特征查询。")
    home_team_name: Optional[str] = Field(None, description="主队官方标准名。")
    away_team_id: Optional[str] = Field(None, description="客队 ID。")
    away_team_name: Optional[str] = Field(None, description="客队官方标准名。")
    kickoff_time: Optional[datetime] = Field(None, description="比赛开球时间 (UTC)。")
    confidence: float = Field(..., ge=0.0, le=1.0, description="解析置信度。")


class StatsAnalysisToolInput(BaseModel):
    """球队/球员统计分析输入。"""

    match_id: str
    scope: Literal["team", "player", "both"] = Field(
        "team", description="分析范围：球队、球员或二者皆有。"
    )
    window: Literal["last5", "last10", "season"] = Field(
        "last5", description="统计窗口：近 5 场 / 10 场 / 赛季。"
    )


class StatsAnalysisToolOutput(BaseModel):
    highlights: List[str] = Field(..., description="关键总结，例如'主队近5场胜率80%'。")
    risk_flags: List[str] = Field(default_factory=list, description="潜在风险提示。")


class HistoricalComparisonToolInput(BaseModel):
    match_id: str
    window: int = Field(5, ge=1, le=20, description="H2H 统计所用的历史场次数。")


class HistoricalComparisonToolOutput(BaseModel):
    h2h_summary: str = Field(..., description="历史交锋结果文字描述。")
    home_home_advantage: float = Field(..., description="主队主场胜率。")
    away_away_advantage: float = Field(..., description="客队客场胜率。")
    key_players: List[str] = Field(default_factory=list, description="关键球员对位分析。")


class TacticalInsightToolInput(BaseModel):
    match_id: str


class TacticalInsightToolOutput(BaseModel):
    preferred_formations: List[str] = Field(..., description="常用阵型列表，例如 ['4-2-3-1']。")
    tactical_style: Literal["possession", "counter", "pressing", "direct", "mixed"]
    coach_notes: str = Field(..., description="最近教练战术调整说明。")


class LiveFeedToolInput(BaseModel):
    match_id: str


class LiveFeedToolOutput(BaseModel):
    possession: Optional[List[float]] = Field(None, description="实时控球率 [主, 客]。")
    shots_on_target: Optional[List[int]] = Field(None, description="射正次数 [主, 客]。")
    key_events: List[str] = Field(default_factory=list, description="进球/红牌等事件列表。")
    alerts: List[str] = Field(default_factory=list, description="与赛前预测偏差的提醒。")


class PostMatchReviewToolInput(BaseModel):
    match_id: str


class PostMatchReviewToolOutput(BaseModel):
    timeline: List[str] = Field(..., description="按时间排序的关键事件。")
    comparison: str = Field(..., description="赛前预测 vs 赛后结果的对比总结。")


class PredictionToolInput(BaseModel):
    match_id: str
    phase: str = Field("T-24h", description="预测时点，例如 T-24h 或 T-1h。")


class PredictionToolOutput(BaseModel):
    model_version: str
    home_win: float = Field(..., ge=0.0, le=1.0)
    draw: float = Field(..., ge=0.0, le=1.0)
    away_win: float = Field(..., ge=0.0, le=1.0)
    explanation: Optional[str] = Field(None, description="简要解释。")


class ScorelinePredictorToolInput(BaseModel):
    match_id: str


class ScorelinePredictorToolOutput(BaseModel):
    top_scorelines: List[str] = Field(..., description="最可能的比分列表，例如 ['1-1', '2-1']。")
    probabilities: List[float] = Field(..., description="对应概率，总和 <= 1。")


class EventPredictorToolInput(BaseModel):
    match_id: str
    event_type: Literal["goals", "corners", "cards", "penalties"]


class EventPredictorToolOutput(BaseModel):
    event_type: str
    buckets: List[str] = Field(..., description="区间或事件名称，如 '0-1 球'。")
    probabilities: List[float] = Field(..., description="与 buckets 一一对应的概率。")


class NewsItemSchema(BaseModel):
    title: str
    summary: str
    source: str = Field(..., description="新闻来源，如 'BBC Sport', 'Twitter'")
    url: Optional[str] = None
    published_at: datetime
    reliability_score: float = Field(0.5, description="可信度评分 0-1")

class NewsToolOutput(BaseModel):
    items: List[NewsItemSchema] = Field(..., description="结构化的资讯列表")
    summary_of_consensus: Optional[str] = Field(None, description="多条新闻的综合摘要")


class OddsToolInput(BaseModel):
    match_id: str

class MarketOption(BaseModel):
    provider: str = Field(..., description="博彩公司名称，如 'Bet365'")
    home_odds: float
    draw_odds: float
    away_odds: float
    implied_prob_home: float = Field(..., description="隐含主胜概率")

class OddsToolOutput(BaseModel):
    markets: List[MarketOption] = Field(..., description="主流公司的盘口列表")
    anomalies: List[str] = Field(default_factory=list, description="赔率异常提示")


class LLMAugmentorToolInput(BaseModel):
    context: str = Field(..., description="结构化特征或事实。")
    evidence: List[str] = Field(default_factory=list, description="引用的资讯/来源。")


class LLMAugmentorToolOutput(BaseModel):
    reasoning_chain: List[str] = Field(..., description="Chain-of-Thought 步骤。")
    final_statement: str = Field(..., description="人类可读的结论。")


class StrategyToolInput(BaseModel):
    preference: Literal["conservative", "balanced", "aggressive"] = "balanced"
    context: str = Field(..., description="需要考虑的比赛或投注背景。")


class StrategyToolOutput(BaseModel):
    recommendation: str
    rationale: str
