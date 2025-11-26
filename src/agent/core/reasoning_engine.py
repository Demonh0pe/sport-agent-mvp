"""
推理引擎 (Reasoning Engine)

这是Agent的核心大脑，负责：
1. 多维度因素分析
2. 因果链构建
3. 置信度评估
4. 反事实推理（What-if分析）
5. 风险因素识别

Author: Sport Agent Team
Date: 2025-11-26
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FactorType(Enum):
    """分析因素类型"""
    RANKING = "ranking"  # 排名差距
    RECENT_FORM = "recent_form"  # 近期状态
    HISTORICAL = "historical"  # 历史交锋
    HOME_AWAY = "home_away"  # 主客场优势
    INJURY = "injury"  # 伤病情况
    TACTICAL = "tactical"  # 战术克制
    SCHEDULE = "schedule"  # 赛程疲劳
    PSYCHOLOGICAL = "psychological"  # 心理因素


class Impact(Enum):
    """影响程度"""
    CRITICAL = "critical"  # 决定性影响 (权重 0.3-0.5)
    MAJOR = "major"  # 重要影响 (权重 0.15-0.3)
    MODERATE = "moderate"  # 中等影响 (权重 0.05-0.15)
    MINOR = "minor"  # 轻微影响 (权重 0.01-0.05)


@dataclass
class Factor:
    """分析因素"""
    factor_type: FactorType
    name: str
    data: Dict[str, Any]
    impact_weight: float  # 影响权重 (0-1)
    direction: str  # "team_a" / "team_b" / "neutral"
    confidence: float  # 置信度 (0-1)
    reasoning: str  # 推理过程


@dataclass
class CausalNode:
    """因果链节点"""
    statement: str  # 陈述
    confidence: float  # 置信度
    evidence: List[str]  # 支撑证据
    next_nodes: List['CausalNode']  # 下一级推理


@dataclass
class ReasoningResult:
    """推理结果"""
    conclusion: str  # 核心结论
    probability: float  # 预测概率
    overall_confidence: float  # 整体置信度
    key_factors: List[Factor]  # 关键因素（按影响权重排序）
    causal_chain: List[str]  # 因果链（文本形式）
    risk_factors: List[Dict[str, Any]]  # 风险因素
    counterfactuals: List[str]  # 反事实分析
    reasoning_trace: str  # 推理过程记录


class ReasoningEngine:
    """
    推理引擎

    核心能力：
    1. 从结构化数据中识别关键因素
    2. 评估每个因素的影响权重和方向
    3. 构建因果推理链
    4. 计算整体置信度
    5. 进行反事实分析（What-if）
    """

    def __init__(self):
        self.factor_weights = self._initialize_weights()
        self.confidence_threshold = 0.6  # 低于此值会标记为"不确定"

    def _initialize_weights(self) -> Dict[FactorType, float]:
        """
        初始化各因素的基础权重

        这些权重是基于足球领域知识设定的，可以通过机器学习优化
        """
        return {
            FactorType.RANKING: 0.25,  # 排名差距
            FactorType.RECENT_FORM: 0.20,  # 近期状态
            FactorType.HISTORICAL: 0.15,  # 历史交锋
            FactorType.HOME_AWAY: 0.15,  # 主客场
            FactorType.INJURY: 0.10,  # 伤病
            FactorType.TACTICAL: 0.08,  # 战术
            FactorType.SCHEDULE: 0.04,  # 赛程
            FactorType.PSYCHOLOGICAL: 0.03,  # 心理
        }

    async def analyze_match_prediction(
        self,
        query: str,
        structured_data: Dict[str, Any],
        comparisons: Dict[str, Any]
    ) -> ReasoningResult:
        """
        主推理入口：分析比赛预测

        Args:
            query: 用户查询
            structured_data: 结构化数据
            comparisons: 对比分析结果

        Returns:
            ReasoningResult: 推理结果
        """
        logger.info(f"[ReasoningEngine] Starting analysis for query: {query}")

        # Step 1: 识别关键因素
        factors = self._identify_factors(structured_data, comparisons)
        logger.info(f"[ReasoningEngine] Identified {len(factors)} factors")

        # Step 2: 评估每个因素的影响
        evaluated_factors = self._evaluate_factors(factors, structured_data)

        # Step 3: 按影响权重排序
        key_factors = sorted(
            evaluated_factors,
            key=lambda f: f.impact_weight,
            reverse=True
        )[:5]  # 取前5个关键因素

        # Step 4: 构建因果链
        causal_chain = self._build_causal_chain(key_factors, structured_data)

        # Step 5: 综合推理得出结论
        conclusion = self._synthesize_conclusion(key_factors, structured_data)

        # Step 6: 计算整体置信度
        overall_confidence = self._calculate_overall_confidence(key_factors)

        # Step 7: 识别风险因素
        risk_factors = self._identify_risk_factors(key_factors, structured_data)

        # Step 8: 反事实分析
        counterfactuals = self._counterfactual_analysis(
            key_factors,
            conclusion,
            structured_data
        )

        # Step 9: 生成推理轨迹
        reasoning_trace = self._generate_reasoning_trace(
            key_factors,
            causal_chain,
            conclusion
        )

        result = ReasoningResult(
            conclusion=conclusion["text"],
            probability=conclusion.get("probability", 0.5),
            overall_confidence=overall_confidence,
            key_factors=key_factors,
            causal_chain=causal_chain,
            risk_factors=risk_factors,
            counterfactuals=counterfactuals,
            reasoning_trace=reasoning_trace
        )

        logger.info(f"[ReasoningEngine] Analysis complete. Confidence: {overall_confidence:.2f}")
        return result

    def _identify_factors(
        self,
        structured_data: Dict[str, Any],
        comparisons: Dict[str, Any]
    ) -> List[Factor]:
        """
        从数据中识别所有可分析的因素

        Returns:
            List[Factor]: 因素列表
        """
        factors = []

        # 1. 排名差距
        if "ranking" in comparisons:
            factors.append(Factor(
                factor_type=FactorType.RANKING,
                name="排名差距",
                data=comparisons["ranking"],
                impact_weight=0.0,  # 待评估
                direction="",  # 待评估
                confidence=0.0,  # 待评估
                reasoning=""  # 待评估
            ))

        # 2. 近期状态
        if "recent_form" in comparisons:
            factors.append(Factor(
                factor_type=FactorType.RECENT_FORM,
                name="近期状态",
                data=comparisons["recent_form"],
                impact_weight=0.0,
                direction="",
                confidence=0.0,
                reasoning=""
            ))

        # 3. 历史交锋
        if "historical" in comparisons:
            factors.append(Factor(
                factor_type=FactorType.HISTORICAL,
                name="历史交锋",
                data=comparisons["historical"],
                impact_weight=0.0,
                direction="",
                confidence=0.0,
                reasoning=""
            ))

        # 4. 主客场优势
        if "home_away" in comparisons:
            factors.append(Factor(
                factor_type=FactorType.HOME_AWAY,
                name="主客场优势",
                data=comparisons["home_away"],
                impact_weight=0.0,
                direction="",
                confidence=0.0,
                reasoning=""
            ))

        return factors

    def _evaluate_factors(
        self,
        factors: List[Factor],
        structured_data: Dict[str, Any]
    ) -> List[Factor]:
        """
        评估每个因素的影响权重、方向和置信度

        这是推理引擎的核心逻辑
        """
        evaluated = []

        for factor in factors:
            # 根据因素类型调用对应的评估方法
            if factor.factor_type == FactorType.RANKING:
                evaluated_factor = self._evaluate_ranking(factor)
            elif factor.factor_type == FactorType.RECENT_FORM:
                evaluated_factor = self._evaluate_recent_form(factor)
            elif factor.factor_type == FactorType.HISTORICAL:
                evaluated_factor = self._evaluate_historical(factor)
            elif factor.factor_type == FactorType.HOME_AWAY:
                evaluated_factor = self._evaluate_home_away(factor)
            else:
                # 其他因素暂时使用默认评估
                evaluated_factor = factor

            evaluated.append(evaluated_factor)

        return evaluated

    def _evaluate_ranking(self, factor: Factor) -> Factor:
        """
        评估排名差距因素

        逻辑：
        - 排名差距越大，影响越大
        - 前5名 vs 后5名：影响权重 0.3-0.4
        - 中游球队互打：影响权重 0.1-0.2
        """
        data = factor.data
        rank_a = data.get("team_a_rank", 10)
        rank_b = data.get("team_b_rank", 10)

        rank_diff = abs(rank_a - rank_b)

        # 计算影响权重
        if rank_diff >= 10:
            impact_weight = 0.35
            significance_text = "悬殊"
        elif rank_diff >= 5:
            impact_weight = 0.25
            significance_text = "明显"
        elif rank_diff >= 2:
            impact_weight = 0.15
            significance_text = "中等"
        else:
            impact_weight = 0.08
            significance_text = "轻微"

        # 确定方向
        direction = "team_a" if rank_a < rank_b else "team_b"
        winner_rank = min(rank_a, rank_b)
        loser_rank = max(rank_a, rank_b)

        # 置信度：排名差距越大，越确定
        confidence = min(0.95, 0.6 + (rank_diff / 20) * 0.35)

        # 推理过程
        reasoning = (
            f"排名差距{significance_text}（{rank_diff}位），"
            f"排名靠前的球队（第{winner_rank}名）整体实力占优"
        )

        factor.impact_weight = impact_weight
        factor.direction = direction
        factor.confidence = confidence
        factor.reasoning = reasoning

        return factor

    def _evaluate_recent_form(self, factor: Factor) -> Factor:
        """评估近期状态因素"""
        data = factor.data

        win_rate_a = data.get("team_a_win_rate", 0.5)
        win_rate_b = data.get("team_b_win_rate", 0.5)

        win_rate_diff = abs(win_rate_a - win_rate_b)

        # 计算状态差距倍数
        if win_rate_b > 0:
            ratio = win_rate_a / win_rate_b if win_rate_a > win_rate_b else win_rate_b / win_rate_a
        else:
            ratio = 2.0

        # 影响权重
        if win_rate_diff >= 0.4:
            impact_weight = 0.28
        elif win_rate_diff >= 0.25:
            impact_weight = 0.20
        elif win_rate_diff >= 0.15:
            impact_weight = 0.12
        else:
            impact_weight = 0.06

        direction = "team_a" if win_rate_a > win_rate_b else "team_b"
        confidence = min(0.9, 0.5 + win_rate_diff)

        better_rate = max(win_rate_a, win_rate_b)
        worse_rate = min(win_rate_a, win_rate_b)

        reasoning = (
            f"近期状态差距明显，状态较好一方胜率{better_rate:.0%}，"
            f"对手仅{worse_rate:.0%}，状态好{ratio:.1f}倍"
        )

        factor.impact_weight = impact_weight
        factor.direction = direction
        factor.confidence = confidence
        factor.reasoning = reasoning

        return factor

    def _evaluate_historical(self, factor: Factor) -> Factor:
        """评估历史交锋因素"""
        data = factor.data

        h2h_a_wins = data.get("team_a_wins", 0)
        h2h_b_wins = data.get("team_b_wins", 0)
        h2h_draws = data.get("draws", 0)
        total = h2h_a_wins + h2h_b_wins + h2h_draws

        if total == 0:
            # 没有历史数据，影响权重为0
            factor.impact_weight = 0.0
            factor.confidence = 0.0
            factor.reasoning = "缺乏历史交锋数据"
            return factor

        win_rate_a = h2h_a_wins / total
        win_rate_b = h2h_b_wins / total

        # 历史优势不如当前状态重要
        if abs(win_rate_a - win_rate_b) >= 0.4:
            impact_weight = 0.15
        elif abs(win_rate_a - win_rate_b) >= 0.2:
            impact_weight = 0.10
        else:
            impact_weight = 0.05

        direction = "team_a" if h2h_a_wins > h2h_b_wins else "team_b"
        confidence = min(0.8, 0.4 + total * 0.08)  # 样本越多，置信度越高

        reasoning = f"历史交锋{total}场，优势方{max(h2h_a_wins, h2h_b_wins)}胜"

        factor.impact_weight = impact_weight
        factor.direction = direction
        factor.confidence = confidence
        factor.reasoning = reasoning

        return factor

    def _evaluate_home_away(self, factor: Factor) -> Factor:
        """评估主客场优势"""
        data = factor.data

        home_advantage = data.get("home_advantage", 0.0)
        away_disadvantage = data.get("away_disadvantage", 0.0)

        # 主场优势通常能提供5-15%的胜率提升
        net_advantage = home_advantage - away_disadvantage

        if abs(net_advantage) >= 0.20:
            impact_weight = 0.18
        elif abs(net_advantage) >= 0.10:
            impact_weight = 0.12
        else:
            impact_weight = 0.06

        direction = "team_a" if net_advantage > 0 else "team_b"
        confidence = 0.75  # 主客场因素相对稳定

        reasoning = f"主场优势明显，净优势{abs(net_advantage):.0%}"

        factor.impact_weight = impact_weight
        factor.direction = direction
        factor.confidence = confidence
        factor.reasoning = reasoning

        return factor

    def _build_causal_chain(
        self,
        factors: List[Factor],
        structured_data: Dict[str, Any]
    ) -> List[str]:
        """
        构建因果推理链

        例如：
        "排名差距大" → "整体实力悬殊" → "利物浦优势明显"
        "近期状态好3倍" → "势头和信心差距" → "利物浦优势明显"

        Returns:
            List[str]: 因果链步骤
        """
        chain = []

        for factor in factors[:3]:  # 取前3个最重要的因素
            # 构建三段式因果链
            # 1. 数据事实
            fact = f"【数据】{factor.name}：{factor.reasoning}"

            # 2. 中间推理
            intermediate = self._get_intermediate_reasoning(factor)

            # 3. 对结论的贡献
            contribution = self._get_contribution(factor)

            chain.append(f"{fact} → {intermediate} → {contribution}")

        return chain

    def _get_intermediate_reasoning(self, factor: Factor) -> str:
        """获取中间推理步骤"""
        if factor.factor_type == FactorType.RANKING:
            return "整体实力差距明显"
        elif factor.factor_type == FactorType.RECENT_FORM:
            return "当前势头和信心存在差距"
        elif factor.factor_type == FactorType.HISTORICAL:
            return "历史心理优势"
        elif factor.factor_type == FactorType.HOME_AWAY:
            return "主场气氛和熟悉度加成"
        else:
            return "影响比赛走向"

    def _get_contribution(self, factor: Factor) -> str:
        """获取因素对结论的贡献"""
        direction_text = "优势方" if factor.direction != "neutral" else "平衡"
        weight_percent = int(factor.impact_weight * 100)
        return f"对{direction_text}贡献{weight_percent}%的影响权重"

    def _synthesize_conclusion(
        self,
        factors: List[Factor],
        structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        综合所有因素，得出最终结论

        采用加权投票机制
        """
        # 统计各方向的总权重
        team_a_weight = sum(f.impact_weight for f in factors if f.direction == "team_a")
        team_b_weight = sum(f.impact_weight for f in factors if f.direction == "team_b")

        total_weight = team_a_weight + team_b_weight

        if total_weight == 0:
            return {
                "text": "双方实力接近，难以预测",
                "probability": 0.5,
                "winner": "draw"
            }

        # 计算概率
        prob_a = team_a_weight / total_weight
        prob_b = team_b_weight / total_weight

        # 确定获胜方
        if prob_a > 0.55:
            winner = "team_a"
            probability = prob_a
            conclusion_text = f"team_a 获胜"
        elif prob_b > 0.55:
            winner = "team_b"
            probability = prob_b
            conclusion_text = f"team_b 获胜"
        else:
            winner = "draw"
            probability = 0.5
            conclusion_text = "双方实力接近，结果难料"

        return {
            "text": conclusion_text,
            "probability": probability,
            "winner": winner
        }

    def _calculate_overall_confidence(self, factors: List[Factor]) -> float:
        """
        计算整体置信度

        综合考虑：
        1. 各因素的置信度
        2. 因素数量
        3. 权重分布
        """
        if not factors:
            return 0.0

        # 加权平均置信度
        weighted_confidence = sum(
            f.confidence * f.impact_weight
            for f in factors
        ) / sum(f.impact_weight for f in factors)

        # 因素数量加成（因素越多，越可靠）
        factor_bonus = min(0.1, len(factors) * 0.02)

        overall = min(0.95, weighted_confidence + factor_bonus)

        return overall

    def _identify_risk_factors(
        self,
        factors: List[Factor],
        structured_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        识别可能改变结果的风险因素

        风险因素：
        1. 弱势一方的优势因素
        2. 不确定性高的因素
        3. 极端情况（伤病、红牌等）
        """
        risks = []

        # 找出预测结论
        team_a_weight = sum(f.impact_weight for f in factors if f.direction == "team_a")
        team_b_weight = sum(f.impact_weight for f in factors if f.direction == "team_b")

        predicted_winner = "team_a" if team_a_weight > team_b_weight else "team_b"
        underdog = "team_b" if predicted_winner == "team_a" else "team_a"

        # 1. 弱势方的优势因素
        for factor in factors:
            if factor.direction == underdog and factor.impact_weight > 0.1:
                risks.append({
                    "type": "underdog_advantage",
                    "factor": factor.name,
                    "description": f"{underdog}的{factor.name}具有优势，可能造成冷门",
                    "impact": factor.impact_weight
                })

        # 2. 低置信度因素
        for factor in factors:
            if factor.confidence < 0.6:
                risks.append({
                    "type": "low_confidence",
                    "factor": factor.name,
                    "description": f"{factor.name}数据不足，存在不确定性",
                    "impact": factor.impact_weight
                })

        # 按影响权重排序
        risks.sort(key=lambda r: r["impact"], reverse=True)

        return risks[:3]  # 返回前3个风险

    def _counterfactual_analysis(
        self,
        factors: List[Factor],
        conclusion: Dict[str, Any],
        structured_data: Dict[str, Any]
    ) -> List[str]:
        """
        反事实分析（What-if）

        模拟如果某些条件改变，结果会如何

        例如：
        - 如果主场优势更大，概率会如何变化
        - 如果核心球员受伤缺阵
        """
        counterfactuals = []

        current_prob = conclusion.get("probability", 0.5)

        # 分析主客场因素
        home_factor = next((f for f in factors if f.factor_type == FactorType.HOME_AWAY), None)
        if home_factor and home_factor.impact_weight > 0.1:
            # 如果主场优势翻倍
            adjusted_prob = min(0.95, current_prob + 0.10)
            counterfactuals.append(
                f"如果主场优势更强 → 获胜概率提升至 {adjusted_prob:.1%}"
            )

        # 分析伤病因素
        # TODO: 当有伤病数据时补充

        # 分析近期状态
        form_factor = next((f for f in factors if f.factor_type == FactorType.RECENT_FORM), None)
        if form_factor and form_factor.impact_weight > 0.15:
            adjusted_prob = max(0.05, current_prob - 0.15)
            counterfactuals.append(
                f"如果近期状态下滑 → 获胜概率降至 {adjusted_prob:.1%}"
            )

        return counterfactuals

    def _generate_reasoning_trace(
        self,
        factors: List[Factor],
        causal_chain: List[str],
        conclusion: Dict[str, Any]
    ) -> str:
        """
        生成推理过程的文本记录

        用于调试和向用户展示推理过程
        """
        trace_lines = [
            "=== 推理过程 ===",
            f"\n1. 识别了 {len(factors)} 个关键因素：",
        ]

        for i, factor in enumerate(factors, 1):
            trace_lines.append(
                f"   {i}. {factor.name} (权重: {factor.impact_weight:.2f}, "
                f"置信度: {factor.confidence:.2f})"
            )

        trace_lines.append("\n2. 因果推理链：")
        for i, chain in enumerate(causal_chain, 1):
            trace_lines.append(f"   {i}. {chain}")

        trace_lines.append(f"\n3. 综合结论：{conclusion['text']}")
        trace_lines.append(f"   概率: {conclusion.get('probability', 0.5):.1%}")

        return "\n".join(trace_lines)
