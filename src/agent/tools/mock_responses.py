"""Mock 工具响应库：为所有工具生成高质量的伪数据

在真实数据源就位前，这个库提供：
1. 确定性的伪数据（基于输入的 hash）
2. 覆盖各种场景（大冷门、势均力敌、单边压倒等）
3. 符合工具 Schema 的结构化响应
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.agent.tools.schemas import (
    MatchResolverToolOutput,
    StatsAnalysisToolOutput,
    HistoricalComparisonToolOutput,
    TacticalInsightToolOutput,
    LiveFeedToolOutput,
    PostMatchReviewToolOutput,
    PredictionToolOutput,
    ScorelinePredictorToolOutput,
    EventPredictorToolOutput,
    NewsToolOutput,
    NewsItemSchema,
    OddsToolOutput,
    MarketOption,
    LLMAugmentorToolOutput,
    StrategyToolOutput,
)


class MockToolResponses:
    """
    Mock 工具响应工厂

    设计原则:
    1. 确定性: 相同的输入参数 → 相同的输出（便于调试）
    2. 多样性: 覆盖各种比赛场景
    3. 真实性: 数据分布接近真实足球比赛
    """

    # ========== 辅助方法 ==========

    @staticmethod
    def _seed_from_input(**kwargs) -> int:
        """从输入参数生成确定性的随机种子"""
        input_str = "|".join(str(v) for v in kwargs.values())
        hash_obj = hashlib.md5(input_str.encode())
        return int(hash_obj.hexdigest(), 16) % 1000

    @staticmethod
    def _seeded_random(seed: int, multiplier: float = 1.0) -> float:
        """基于种子生成伪随机数 [0, 1)"""
        random.seed(seed)
        return random.random() * multiplier

    # ========== MatchResolverTool ==========

    @staticmethod
    def match_resolver(
        query: str,
        league_hint: Optional[str] = None,
        date_hint: Optional[str] = None,
    ) -> MatchResolverToolOutput:
        """
        将自然语言查询解析为比赛 ID

        示例输入:
        - "Barcelona next match"
        - "Manchester United vs Liverpool"
        - "Milan derby"
        """
        seed = MockToolResponses._seed_from_input(query=query, league_hint=league_hint)

        # 伪造一个 match_id
        query_normalized = query.lower().replace(" ", "_")[:20]
        match_id = f"{query_normalized}_{seed % 1000:04d}"

        # 伪造球队信息
        team_pairs = [
            ("FC Barcelona", "Real Madrid"),
            ("Manchester United", "Liverpool FC"),
            ("AC Milan", "Inter Milan"),
            ("Bayern Munich", "Borussia Dortmund"),
            ("Paris Saint-Germain", "Olympique Lyon"),
        ]
        home_team, away_team = team_pairs[seed % len(team_pairs)]

        return MatchResolverToolOutput(
            match_id=match_id,
            home_team_id=home_team.lower().replace(" ", "_"),
            home_team_name=home_team,
            away_team_id=away_team.lower().replace(" ", "_"),
            away_team_name=away_team,
            kickoff_time=datetime.now(timezone.utc),
            confidence=0.85 + (seed % 15) / 100,  # 0.85 - 0.99
        )

    # ========== StatsAnalysisTool ==========

    @staticmethod
    def stats_analysis(
        match_id: str,
        scope: str = "team",
        window: str = "last5",
    ) -> StatsAnalysisToolOutput:
        """分析球队/球员统计数据"""
        seed = MockToolResponses._seed_from_input(match_id=match_id, scope=scope)

        highlights = []
        risk_flags = []

        if scope in ("team", "both"):
            # 球队统计
            win_rate = 0.4 + MockToolResponses._seeded_random(seed) * 0.5
            highlights.append(
                f"主队最近 {window} 场胜率 {win_rate:.1%}，"
                f"{'明显高于' if win_rate > 0.6 else '略低于'} 联赛平均水平"
            )

            goals_per_game = 1.2 + MockToolResponses._seeded_random(seed + 1) * 2
            highlights.append(f"主队场均进球 {goals_per_game:.1f}")

            goals_against = 0.8 + MockToolResponses._seeded_random(seed + 2) * 1.5
            if goals_against > 1.5:
                risk_flags.append("防守端承压，失球数偏高")

        if scope in ("player", "both"):
            # 球员统计
            highlights.append("关键前锋最近状态火热，进球助攻均有贡献")
            highlights.append("中场核心传球成功率 87%，组织能力稳定")

        return StatsAnalysisToolOutput(
            highlights=highlights,
            risk_flags=risk_flags,
        )

    # ========== HistoricalComparisonTool ==========

    @staticmethod
    def historical_comparison(
        match_id: str,
        window: int = 5,
    ) -> HistoricalComparisonToolOutput:
        """H2H 与主客场对比"""
        seed = MockToolResponses._seed_from_input(match_id=match_id, window=window)

        # H2H 战绩
        home_wins = seed % window
        away_wins = (seed + 1) % window
        draws = max(0, window - home_wins - away_wins)

        h2h_summary = (
            f"最近 {window} 次交锋，主队赢 {home_wins} 场，"
            f"客队赢 {away_wins} 场，平 {draws} 场。"
            f"{'主队略占上风' if home_wins > away_wins else '势均力敌'}"
        )

        home_home_advantage = 0.5 + MockToolResponses._seeded_random(seed) * 0.3
        away_away_advantage = 0.5 + MockToolResponses._seeded_random(seed + 1) * 0.3

        key_players = [
            "前锋 A (近 3 场 2 球 1 助)",
            "中场 B (传中能力强)",
            "后卫 C (防线支柱)",
        ]

        return HistoricalComparisonToolOutput(
            h2h_summary=h2h_summary,
            home_home_advantage=home_home_advantage,
            away_away_advantage=away_away_advantage,
            key_players=key_players,
        )

    # ========== TacticalInsightTool ==========

    @staticmethod
    def tactical_insight(match_id: str) -> TacticalInsightToolOutput:
        """阵型与战术分析"""
        seed = MockToolResponses._seed_from_input(match_id=match_id)

        formations = ["4-2-3-1", "4-3-3", "3-5-2", "5-3-2"]
        preferred = [formations[seed % len(formations)]]

        tactical_styles = ["possession", "counter", "pressing", "direct", "mixed"]
        style = tactical_styles[seed % len(tactical_styles)]

        coach_notes = (
            f"近期主要采用 {preferred[0]} 阵型，"
            f"战术风格偏向{style}。"
            f"上一场对 Y 队进行了临时调整，效果显著。"
        )

        return TacticalInsightToolOutput(
            preferred_formations=preferred,
            tactical_style=style,
            coach_notes=coach_notes,
        )

    # ========== LiveFeedTool ==========

    @staticmethod
    def live_feed(match_id: str) -> LiveFeedToolOutput:
        """赛中实时数据"""
        seed = MockToolResponses._seed_from_input(match_id=match_id)

        possession = [
            0.45 + MockToolResponses._seeded_random(seed) * 0.1,
            0.55 - MockToolResponses._seeded_random(seed) * 0.1,
        ]
        # 归一化
        total = sum(possession)
        possession = [p / total for p in possession]

        shots_on_target = [seed % 8, (seed + 1) % 8]

        key_events = [
            "36' 进球 - 前锋A破门",
            "52' 黄牌 - 后卫B",
            "71' 换人 - 中场C下场，替补D上场",
        ]

        alerts = []
        if possession[0] < 0.4:
            alerts.append("主队控球率低于预期，需加强进攻")
        if shots_on_target[1] > shots_on_target[0] * 1.5:
            alerts.append("客队射正效率偏高，防线需加强")

        return LiveFeedToolOutput(
            possession=possession,
            shots_on_target=shots_on_target,
            key_events=key_events,
            alerts=alerts,
        )

    # ========== PostMatchReviewTool ==========

    @staticmethod
    def post_match_review(match_id: str) -> PostMatchReviewToolOutput:
        """赛后复盘"""
        seed = MockToolResponses._seed_from_input(match_id=match_id)

        timeline = [
            "12' - 主队传中，前锋头球偏出",
            "28' - 客队反击，接近破门，门神反应神速",
            "35' - 主队前锋在禁区内被犯规，获得点球",
            "36' - 点球破门，主队 1-0 领先",
            "56' - 客队替补上阵，加强进攻",
            "67' - 客队扳平，1-1",
            "85' - 主队后卫后场送礼，客队逆转",
            "90+3' - 最终比分 1-2",
        ]

        comparison = (
            "赛前预测主队赢概率 58%，但实际表现平庸。"
            "控球率符合预期，但禁区把握机会能力不足。"
            "客队体能储备充足，下半场逆转说明准备充分。"
        )

        return PostMatchReviewToolOutput(
            timeline=timeline,
            comparison=comparison,
        )

    # ========== PredictionTool ==========

    @staticmethod
    def prediction(match_id: str, phase: str = "T-24h") -> PredictionToolOutput:
        """胜平负概率预测"""
        seed = MockToolResponses._seed_from_input(match_id=match_id, phase=phase)

        # 基于 seed 生成概率
        home_base = 0.35 + MockToolResponses._seeded_random(seed) * 0.4
        away_base = 0.2 + MockToolResponses._seeded_random(seed + 1) * 0.35
        draw_base = 1.0 - home_base - away_base

        # 归一化
        total = home_base + away_base + draw_base
        home_win = home_base / total
        draw = draw_base / total
        away_win = away_base / total

        return PredictionToolOutput(
            model_version="xgb_v2.1",
            home_win=round(home_win, 3),
            draw=round(draw, 3),
            away_win=round(away_win, 3),
            explanation="基于球队近期表现、H2H 历史和伤病情况综合评估",
        )

    # ========== ScorelinePredictorTool ==========

    @staticmethod
    def scoreline_predictor(match_id: str) -> ScorelinePredictorToolOutput:
        """比分预测"""
        seed = MockToolResponses._seed_from_input(match_id=match_id)

        # 最常见的比分
        scorelines = ["1-1", "2-1", "1-0", "2-0", "0-1"]
        top_scorelines = scorelines[:3]

        probabilities = [
            0.25 + MockToolResponses._seeded_random(seed) * 0.15,
            0.20 + MockToolResponses._seeded_random(seed + 1) * 0.15,
            0.15 + MockToolResponses._seeded_random(seed + 2) * 0.10,
        ]

        # 归一化
        total = sum(probabilities)
        probabilities = [round(p / total, 3) for p in probabilities]

        return ScorelinePredictorToolOutput(
            top_scorelines=top_scorelines,
            probabilities=probabilities,
        )

    # ========== EventPredictorTool ==========

    @staticmethod
    def event_predictor(
        match_id: str,
        event_type: str = "goals",
    ) -> EventPredictorToolOutput:
        """事件预测（进球、角球、黄牌等）"""
        seed = MockToolResponses._seed_from_input(match_id=match_id, event_type=event_type)

        event_configs = {
            "goals": {
                "buckets": ["0-1 球", "2-3 球", "4+ 球"],
                "base_probs": [0.35, 0.45, 0.20],
            },
            "corners": {
                "buckets": ["0-4 球", "5-8 球", "9+ 球"],
                "base_probs": [0.25, 0.50, 0.25],
            },
            "cards": {
                "buckets": ["0-1 张", "2-3 张", "4+ 张"],
                "base_probs": [0.40, 0.40, 0.20],
            },
            "penalties": {
                "buckets": ["无", "1 个", "2+ 个"],
                "base_probs": [0.85, 0.13, 0.02],
            },
        }

        config = event_configs.get(event_type, event_configs["goals"])
        buckets = config["buckets"]
        base_probs = config["base_probs"]

        # 添加随机波动
        probs = [
            p + (MockToolResponses._seeded_random(seed + i) - 0.5) * 0.1
            for i, p in enumerate(base_probs)
        ]

        # 确保非负且和为 1
        probs = [max(0, p) for p in probs]
        total = sum(probs)
        probs = [round(p / total, 3) for p in probs]

        return EventPredictorToolOutput(
            event_type=event_type,
            buckets=buckets,
            probabilities=probs,
        )

    # ========== NewsTool ==========

    @staticmethod
    def news(
        entity_id: str,
        entity_type: str = "team",
        window_hours: int = 72,
    ) -> NewsToolOutput:
        """获取资讯"""
        seed = MockToolResponses._seed_from_input(entity_id=entity_id, window_hours=window_hours)

        news_templates = [
            NewsItemSchema(
                title=f"{entity_id} 官方宣布新赛季大名单",
                summary="主力前锋伤愈复出，防线迎来补强",
                source="Official Club",
                published_at=datetime.now(timezone.utc),
                reliability_score=0.95,
            ),
            NewsItemSchema(
                title=f"{entity_id} 教练战术调整引热议",
                summary="改用 4-2-3-1 阵型，球迷评价不一",
                source="Sports Media",
                published_at=datetime.now(timezone.utc),
                reliability_score=0.75,
            ),
            NewsItemSchema(
                title=f"{entity_id} 关键球员伤病情况更新",
                summary="核心后卫预计下周复出",
                source="Team News",
                published_at=datetime.now(timezone.utc),
                reliability_score=0.85,
            ),
        ]

        items = news_templates[: (seed % 3) + 1]

        summary = f"{entity_id} 近期动态：阵容调整完成，战术创新备战。"

        return NewsToolOutput(
            items=items,
            summary_of_consensus=summary,
        )

    # ========== OddsTool ==========

    @staticmethod
    def odds(match_id: str) -> OddsToolOutput:
        """赔率与市场异常"""
        seed = MockToolResponses._seed_from_input(match_id=match_id)

        # 基于概率反向生成赔率
        pred = MockToolResponses.prediction(match_id)
        home_odds = round(1 / (pred.home_win + 0.01), 2)
        draw_odds = round(1 / (pred.draw + 0.01), 2)
        away_odds = round(1 / (pred.away_win + 0.01), 2)

        markets = [
            MarketOption(
                provider="Bet365",
                home_odds=home_odds,
                draw_odds=draw_odds,
                away_odds=away_odds,
                implied_prob_home=round(1 / home_odds, 3),
            ),
            MarketOption(
                provider="WilliamHill",
                home_odds=home_odds * (0.98 + MockToolResponses._seeded_random(seed) * 0.04),
                draw_odds=draw_odds,
                away_odds=away_odds,
                implied_prob_home=round(1 / (home_odds * (0.98 + MockToolResponses._seeded_random(seed) * 0.04)), 3),
            ),
        ]

        anomalies = []
        if seed % 5 == 0:
            anomalies.append("客队赔率近 2 小时大幅波动，可能有伤病消息")

        return OddsToolOutput(
            markets=markets,
            anomalies=anomalies,
        )

    # ========== LLMAugmentorTool ==========

    @staticmethod
    def llm_augmentor(
        context: str,
        evidence: List[str] = None,
    ) -> LLMAugmentorToolOutput:
        """LLM 增强的推理与生成"""
        seed = MockToolResponses._seed_from_input(context=context)

        reasoning_chain = [
            "第一步：分析球队近期表现和伤病情况",
            "第二步：对比历史交锋和主客场差异",
            "第三步：结合市场赔率和舆论情绪",
            "第四步：综合各方面因素得出结论",
        ]

        final_statement = (
            "综合上述因素，主队虽然状态稳定但缺乏关键球员，"
            "客队则趁虚而入。预测本场战平概率最高，其次是客队胜。"
        )

        return LLMAugmentorToolOutput(
            reasoning_chain=reasoning_chain,
            final_statement=final_statement,
        )

    # ========== StrategyTool ==========

    @staticmethod
    def strategy(
        preference: str = "balanced",
        context: str = "",
    ) -> StrategyToolOutput:
        """投注策略建议"""
        strategies = {
            "conservative": {
                "recommendation": "建议下注客队或平局，风险较低",
                "rationale": "主队伤病较多，客队整体状态更佳",
            },
            "balanced": {
                "recommendation": "建议跟进市场共识，选择最高概率结果",
                "rationale": "综合多维度数据，平衡收益与风险",
            },
            "aggressive": {
                "recommendation": "考虑大冷门选项：客队胜",
                "rationale": "市场可能低估了客队的机会",
            },
        }

        strategy = strategies.get(preference, strategies["balanced"])

        return StrategyToolOutput(
            recommendation=strategy["recommendation"],
            rationale=strategy["rationale"],
        )
