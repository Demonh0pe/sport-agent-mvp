"""预测服务骨架：后续将对接特征仓与模型推理。
当前实现返回伪数据，便于 API 端到端联调。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from src.services.api.schemas.prediction import (
    ExplanationFactor,
    PredictionExplanation,
    PredictionResponse,
    ProbabilityBreakdown,
)
from src.shared.config import Settings


class PredictionService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._config = settings.service.prediction_service
        self._model_version = settings.model["prediction"]["active_version"]

    def _pseudo_probability(self, match_id: str, phase: str) -> ProbabilityBreakdown:
        base_seed = abs(hash((match_id, phase))) % 1000 / 1000
        home = 0.35 + (base_seed - 0.5) * 0.3
        away = 0.35 - (base_seed - 0.5) * 0.2
        draw = 1.0 - home - away
        probs = [max(0.05, p) for p in (home, draw, away)]
        total = sum(probs)
        normalized = [p / total for p in probs]
        return ProbabilityBreakdown(home_win=normalized[0], draw=normalized[1], away_win=normalized[2])

    def _build_explanation(self, probabilities: ProbabilityBreakdown) -> PredictionExplanation:
        top_outcome = max(
            (("主胜", probabilities.home_win), ("平局", probabilities.draw), ("客胜", probabilities.away_win)),
            key=lambda item: item[1],
        )
        summary = f"模型推断本场最可能的结果是{top_outcome[0]}，当前置信度 {top_outcome[1]:.2f}."
        factors = [
            ExplanationFactor(
                name="home_win_rate_last5",
                value=0.68,
                impact="positive",
                comment="主队近5场胜率 68%，明显高于联赛均值",
            ),
            ExplanationFactor(
                name="away_goals_conceded_last5",
                value=2.1,
                impact="positive",
                comment="客队近5场场均失球 2.1 个，防守端承压",
            ),
            ExplanationFactor(
                name="h2h_win_rate_home_last5",
                value=0.6,
                impact="positive",
                comment="最近 5 次交锋主队赢下 3 场",
            ),
        ]
        return PredictionExplanation(summary=summary, factors=factors)

    def get_prediction(self, match_id: str, phase: str | None = None, explain: bool = False) -> PredictionResponse:
        phase = phase or self._config.get("default_phase", "T-24h")
        probabilities = self._pseudo_probability(match_id, phase)
        explanation = self._build_explanation(probabilities) if explain else None
        uncertainty_flag = max(probabilities.home_win, probabilities.draw, probabilities.away_win) < 0.45
        return PredictionResponse(
            match_id=match_id,
            phase=phase,
            model_version=self._model_version,
            generated_at=datetime.now(timezone.utc),
            probabilities=probabilities,
            cold_start=False,
            uncertainty_flag=uncertainty_flag,
            explanation=explanation,
        )
