"""
PredictService - 预测服务层

职责：
1. 聚合 StatsService 特征
2. 调用预测模型（规则 + 机器学习）
3. 输出胜平负概率与可解释性结果

注意：
- 纯 Python 实现，不依赖 LangChain
- 依赖 StatsService 获取特征
- 集成现有的 ML 模型
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import date

from src.services.stats_service import stats_service
from src.services.data_service import data_service
from src.services.config import prediction_config

logger = logging.getLogger(__name__)


# ==================== 数据类定义 ====================

@dataclass
class PredictionResult:
    """预测结果"""
    home_team: str
    away_team: str
    
    # 预测概率
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    
    # 预测结果
    predicted_outcome: str  # "HOME_WIN" / "DRAW" / "AWAY_WIN"
    confidence: float  # 0-1
    
    # 可解释性
    key_factors: List[str]  # 关键影响因素
    feature_contributions: Dict[str, float]  # 特征贡献度
    
    # 元数据
    model_version: str
    prediction_time: str
    data_quality_score: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Factor:
    """影响因素"""
    name: str
    value: Any
    impact: str  # "positive" / "negative" / "neutral"
    description: str


# ==================== PredictService ====================

class PredictService:
    """
    预测服务
    
    预测目标：
    - 胜平负预测 (Home Win / Draw / Away Win)
    - 概率分布
    - 可解释性输出
    
    预测方法：
    1. 基于规则的基线模型（Phase 1）
    2. 机器学习模型（Phase 2 - 集成现有模型）
    """
    
    def __init__(self):
        self._stats_service = stats_service
        self._data_service = data_service
        self._config = prediction_config
        self._model_version = self._config.MODEL_VERSION
    
    async def predict_match(
        self,
        home_team_name: str,
        away_team_name: str,
        reference_date: Optional[date] = None
    ) -> Optional[PredictionResult]:
        """
        预测比赛结果
        
        Args:
            home_team_name: 主队名称
            away_team_name: 客队名称
            reference_date: 参考日期（用于计算截止该日期的特征）
            
        Returns:
            预测结果
        """
        # 1. 获取统计特征
        features = await self._stats_service.compute_match_features(
            home_team_name=home_team_name,
            away_team_name=away_team_name,
            reference_date=reference_date
        )
        
        if not features:
            logger.warning(f"Failed to compute features for {home_team_name} vs {away_team_name}")
            return None
        
        # 2. 计算预测概率（基于规则的基线模型）
        probabilities = await self._compute_baseline_probabilities(features)
        
        # 3. 确定预测结果
        predicted_outcome, confidence = self._determine_outcome(probabilities)
        
        # 4. 生成可解释性输出
        key_factors = self._extract_key_factors(features)
        feature_contributions = self._compute_feature_contributions(features)
        
        # 5. 评估数据质量
        data_quality = self._assess_data_quality(features)
        
        from datetime import datetime
        
        return PredictionResult(
            home_team=home_team_name,
            away_team=away_team_name,
            home_win_prob=round(probabilities["home_win"], 3),
            draw_prob=round(probabilities["draw"], 3),
            away_win_prob=round(probabilities["away_win"], 3),
            predicted_outcome=predicted_outcome,
            confidence=round(confidence, 3),
            key_factors=key_factors,
            feature_contributions=feature_contributions,
            model_version=self._model_version,
            prediction_time=datetime.now().isoformat(),
            data_quality_score=round(data_quality, 2)
        )
    
    async def predict_match_by_id(
        self,
        match_id: int
    ) -> Optional[PredictionResult]:
        """
        根据比赛 ID 进行预测
        
        Args:
            match_id: 比赛 ID
            
        Returns:
            预测结果
        """
        match = await self._data_service.get_match(match_id)
        if not match:
            logger.warning(f"Match not found: {match_id}")
            return None
        
        return await self.predict_match(
            home_team_name=match.home_team.name,
            away_team_name=match.away_team.name,
            reference_date=match.match_date.date()
        )
    
    # ==================== 预测模型 ====================
    
    async def _compute_baseline_probabilities(
        self,
        features: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        基于规则的基线模型
        
        考虑因素：
        1. 近期状态（胜率、进球数）
        2. 主场优势
        3. 历史交锋
        4. 积分榜位置
        5. 赛程疲劳度
        
        Returns:
            概率字典: {"home_win": 0.4, "draw": 0.3, "away_win": 0.3}
        """
        home = features.get("home_team", {})
        away = features.get("away_team", {})
        h2h = features.get("head_to_head")
        
        # 初始概率（主场优势基础）
        home_win_prob = self._config.INITIAL_HOME_WIN_PROB
        draw_prob = self._config.INITIAL_DRAW_PROB
        away_win_prob = self._config.INITIAL_AWAY_WIN_PROB
        
        # 因素1: 近期状态调整
        home_form = home.get("form")
        away_form = away.get("form")
        
        if home_form and away_form:
            home_win_rate = home_form.get("win_rate", 0)
            away_win_rate = away_form.get("win_rate", 0)
            
            # 胜率差异调整
            win_rate_diff = (home_win_rate - away_win_rate) * self._config.FORM_WEIGHT
            home_win_prob += win_rate_diff
            away_win_prob -= win_rate_diff
        
        # 因素2: 主客场表现调整
        home_home_stats = home.get("home_stats")
        away_away_stats = away.get("away_stats")
        
        if home_home_stats and away_away_stats:
            home_home_wr = home_home_stats.get("win_rate", 0)
            away_away_wr = away_away_stats.get("win_rate", 0)
            
            # 主客场优势调整
            venue_adj = (home_home_wr - away_away_wr) * self._config.VENUE_WEIGHT
            home_win_prob += venue_adj
            away_win_prob -= venue_adj
        
        # 因素3: 积分榜位置调整
        home_pos = home.get("standing_position")
        away_pos = away.get("standing_position")
        
        if home_pos and away_pos:
            # 排名越高，概率越高
            pos_diff = (away_pos - home_pos) * self._config.POSITION_WEIGHT
            pos_diff = max(-self._config.MAX_POSITION_ADJUSTMENT, 
                          min(self._config.MAX_POSITION_ADJUSTMENT, pos_diff))
            home_win_prob += pos_diff
            away_win_prob -= pos_diff
        
        # 因素4: 历史交锋调整
        if h2h and h2h.get("total_matches", 0) >= self._config.MIN_H2H_MATCHES:
            total = h2h["total_matches"]
            a_wins = h2h.get("team_a_wins", 0)  # team_a 是主队
            b_wins = h2h.get("team_b_wins", 0)
            
            h2h_home_rate = a_wins / total if total > 0 else 0.5
            h2h_away_rate = b_wins / total if total > 0 else 0.5
            
            # H2H 调整
            h2h_adj = (h2h_home_rate - h2h_away_rate) * self._config.H2H_WEIGHT
            home_win_prob += h2h_adj
            away_win_prob -= h2h_adj
        
        # 因素5: 赛程疲劳度调整
        home_density = home.get("schedule_density")
        away_density = away.get("schedule_density")
        
        if home_density and home_density.get("is_congested"):
            home_win_prob -= self._config.CONGESTION_PENALTY
            draw_prob += self._config.CONGESTION_DRAW_BONUS
            away_win_prob += self._config.CONGESTION_DRAW_BONUS
        
        if away_density and away_density.get("is_congested"):
            away_win_prob -= self._config.CONGESTION_PENALTY
            draw_prob += self._config.CONGESTION_DRAW_BONUS
            home_win_prob += self._config.CONGESTION_DRAW_BONUS
        
        # 归一化概率（确保和为1）
        total_prob = home_win_prob + draw_prob + away_win_prob
        
        return {
            "home_win": max(self._config.MIN_PROBABILITY, 
                           min(self._config.MAX_WIN_PROBABILITY, home_win_prob / total_prob)),
            "draw": max(self._config.MIN_PROBABILITY, 
                       min(self._config.MAX_DRAW_PROBABILITY, draw_prob / total_prob)),
            "away_win": max(self._config.MIN_PROBABILITY, 
                           min(self._config.MAX_WIN_PROBABILITY, away_win_prob / total_prob))
        }
    
    def _determine_outcome(
        self,
        probabilities: Dict[str, float]
    ) -> tuple[str, float]:
        """
        根据概率确定预测结果和置信度
        
        Returns:
            (predicted_outcome, confidence)
        """
        home_prob = probabilities["home_win"]
        draw_prob = probabilities["draw"]
        away_prob = probabilities["away_win"]
        
        max_prob = max(home_prob, draw_prob, away_prob)
        
        if max_prob == home_prob:
            outcome = "HOME_WIN"
            confidence = home_prob
        elif max_prob == away_prob:
            outcome = "AWAY_WIN"
            confidence = away_prob
        else:
            outcome = "DRAW"
            confidence = draw_prob
        
        return outcome, confidence
    
    # ==================== 可解释性 ====================
    
    def _extract_key_factors(
        self,
        features: Dict[str, Any]
    ) -> List[str]:
        """
        提取关键影响因素（用于解释预测）
        
        Returns:
            关键因素列表
        """
        factors = []
        
        home = features.get("home_team", {})
        away = features.get("away_team", {})
        
        # 近期状态
        home_form = home.get("form")
        away_form = away.get("form")
        
        if home_form:
            if home_form.get("win_rate", 0) >= self._config.GOOD_FORM_THRESHOLD:
                factors.append(f"{home['name']} 近期状态出色（胜率 {home_form['win_rate']:.1%}）")
            elif home_form.get("win_rate", 0) <= self._config.POOR_FORM_THRESHOLD:
                factors.append(f"{home['name']} 近期状态低迷（胜率 {home_form['win_rate']:.1%}）")
        
        if away_form:
            if away_form.get("win_rate", 0) >= self._config.GOOD_FORM_THRESHOLD:
                factors.append(f"{away['name']} 近期状态出色（胜率 {away_form['win_rate']:.1%}）")
            elif away_form.get("win_rate", 0) <= self._config.POOR_FORM_THRESHOLD:
                factors.append(f"{away['name']} 近期状态低迷（胜率 {away_form['win_rate']:.1%}）")
        
        # 主场优势
        home_home_stats = home.get("home_stats")
        if home_home_stats and home_home_stats.get("win_rate", 0) >= self._config.EXCELLENT_HOME_THRESHOLD:
            factors.append(f"{home['name']} 主场战绩优异（主场胜率 {home_home_stats['win_rate']:.1%}）")
        
        # 赛程疲劳
        home_density = home.get("schedule_density")
        away_density = away.get("schedule_density")
        
        if home_density and home_density.get("is_congested"):
            factors.append(f"{home['name']} 赛程密集，可能存在疲劳")
        
        if away_density and away_density.get("is_congested"):
            factors.append(f"{away['name']} 赛程密集，可能存在疲劳")
        
        # 历史交锋
        h2h = features.get("head_to_head")
        if h2h and h2h.get("total_matches", 0) >= self._config.MIN_H2H_MATCHES:
            a_wins = h2h.get("team_a_wins", 0)
            b_wins = h2h.get("team_b_wins", 0)
            if a_wins > b_wins * self._config.H2H_ADVANTAGE_MULTIPLIER:
                factors.append(f"历史交锋中 {home['name']} 占据明显优势")
            elif b_wins > a_wins * self._config.H2H_ADVANTAGE_MULTIPLIER:
                factors.append(f"历史交锋中 {away['name']} 占据明显优势")
        
        # 如果没有显著因素，添加通用说明
        if not factors:
            factors.append("双方实力接近，比赛胜负难料")
        
        return factors[:self._config.MAX_KEY_FACTORS]
    
    def _compute_feature_contributions(
        self,
        features: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        计算各特征的贡献度（用于详细解释）
        
        Returns:
            特征贡献度字典
        """
        contributions = {k: 0.0 for k in self._config.FEATURE_WEIGHTS.keys()}
        
        home = features.get("home_team", {})
        away = features.get("away_team", {})
        
        # 计算各项贡献
        home_form = home.get("form")
        away_form = away.get("form")
        
        if home_form:
            contributions["home_recent_form"] = (
                home_form.get("win_rate", 0) * self._config.FEATURE_WEIGHTS["home_recent_form"]
            )
        
        if away_form:
            contributions["away_recent_form"] = (
                away_form.get("win_rate", 0) * self._config.FEATURE_WEIGHTS["away_recent_form"]
            )
        
        home_home_stats = home.get("home_stats")
        if home_home_stats:
            contributions["home_advantage"] = (
                home_home_stats.get("win_rate", 0) * self._config.FEATURE_WEIGHTS["home_advantage"]
            )
        
        return contributions
    
    def _assess_data_quality(
        self,
        features: Dict[str, Any]
    ) -> float:
        """
        评估数据质量
        
        Returns:
            质量分数 (0-1)
        """
        quality_score = 1.0
        
        # 检查关键数据是否完整
        home = features.get("home_team", {})
        away = features.get("away_team", {})
        
        if not home.get("form"):
            quality_score -= self._config.QUALITY_WEIGHTS["form_missing"]
        
        if not away.get("form"):
            quality_score -= self._config.QUALITY_WEIGHTS["form_missing"]
        
        if not home.get("home_stats"):
            quality_score -= self._config.QUALITY_WEIGHTS["home_away_stats_missing"]
        
        if not away.get("away_stats"):
            quality_score -= self._config.QUALITY_WEIGHTS["home_away_stats_missing"]
        
        if not features.get("head_to_head"):
            quality_score -= self._config.QUALITY_WEIGHTS["h2h_missing"]
        
        return max(0.0, quality_score)


# 全局单例
predict_service = PredictService()

