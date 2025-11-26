"""
赛事总结模块 (Match Summary Module)

用户场景：
- "总结一下曼联vs利物浦这场比赛"
- "简要说明曼联最近的情况"
- "快速了解英超积分榜情况"

核心功能：
- 单场比赛总结
- 球队阶段性总结
- 联赛整体概况

特点：简洁、快速、要点清晰
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# 导入工具
from src.agent.tools.match_tool import match_tool
from src.agent.tools.standings_tool import standings_tool
from src.agent.tools.stats_tool import stats_tool

# 导入LLM客户端
from src.shared.llm_client import llm_client

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """总结结果"""
    summary_type: str  # "single_match" / "team_period" / "league_overview"
    summary_text: str  # 总结文本
    key_points: List[str]  # 关键要点
    metadata: Dict[str, Any] = None  # 元数据


class MatchSummaryModule:
    """
    赛事总结模块

    特点：简洁、快速、要点清晰
    """

    def __init__(self):
        pass

    async def execute(self, query: str, entities: Dict[str, Any]) -> SummaryResult:
        """
        执行总结

        Args:
            query: 用户原始查询
            entities: 提取的实体

        Returns:
            SummaryResult: 总结结果
        """
        logger.info(f"[MatchSummaryModule] Processing query: {query}")
        logger.info(f"[MatchSummaryModule] Entities: {entities}")

        # 1. 识别总结类型
        summary_type = self._detect_summary_type(query, entities)
        logger.info(f"[MatchSummaryModule] Summary type: {summary_type}")

        # 2. 收集关键信息
        data = await self._collect_key_info(entities, summary_type)

        # 3. 用LLM生成摘要
        summary_text = await self._generate_summary(query, data, summary_type)

        # 4. 提取关键要点
        key_points = self._extract_key_points(summary_text)

        return SummaryResult(
            summary_type=summary_type,
            summary_text=summary_text,
            key_points=key_points,
            metadata={"query": query, "entities": entities}
        )

    def _detect_summary_type(self, query: str, entities: Dict) -> str:
        """
        识别总结类型

        逻辑：
        - 有"比赛"、"vs" → 单场比赛总结
        - 有"联赛"、"积分榜" → 联赛概况
        - 默认 → 球队阶段总结
        """
        query_lower = query.lower()

        # 单场比赛总结
        if any(k in query_lower for k in ["比赛", "vs", "对阵", "交锋"]):
            if 'team_b' in entities:
                return "single_match"

        # 联赛概况
        if any(k in query_lower for k in ["联赛", "积分榜", "整体", "概况"]):
            return "league_overview"

        # 默认：球队阶段总结
        return "team_period"

    async def _collect_key_info(
        self,
        entities: Dict,
        summary_type: str
    ) -> str:
        """
        收集关键信息

        Returns:
            原始数据文本
        """
        try:
            if summary_type == "single_match":
                # 单场比赛：两队数据
                team_a = entities.get('team_a') or entities.get('team')
                team_b = entities.get('team_b')

                if not team_a or not team_b:
                    return "缺少比赛双方信息"

                # 获取两队近期数据
                data_a = await stats_tool.get_team_stats(team_a, last_n=5)
                data_b = await stats_tool.get_team_stats(team_b, last_n=5)

                combined = f"# {team_a} 近期数据\n{data_a}\n\n# {team_b} 近期数据\n{data_b}"
                return combined

            elif summary_type == "team_period":
                # 球队阶段：战绩 + 排名
                team = entities.get('team') or entities.get('team_a')

                if not team:
                    return "缺少球队信息"

                stats = await stats_tool.get_team_stats(team, last_n=10)
                standing = await standings_tool.get_team_standing(team)

                combined = f"{stats}\n\n{standing}"
                return combined

            elif summary_type == "league_overview":
                # 联赛概况：积分榜前几名
                league = entities.get('league')

                # TODO: 实现获取联赛整体数据
                return "联赛概况功能开发中..."

            else:
                return "未知的总结类型"

        except Exception as e:
            logger.error(f"[MatchSummaryModule] Data collection failed: {e}", exc_info=True)
            return f"数据收集失败：{str(e)}"

    async def _generate_summary(
        self,
        query: str,
        data: str,
        summary_type: str
    ) -> str:
        """
        用LLM生成摘要

        特点：简洁、要点清晰
        """
        system_prompt = self._get_system_prompt(summary_type)

        user_prompt = f"""
用户需求：{query}

信息：
{data}

请生成简洁的摘要（控制在150-200字）。
"""

        try:
            summary = await llm_client.generate(
                system_prompt,
                user_prompt,
                # temperature=0.5  # 降低温度，更客观（如果使用v2客户端）
            )
            return summary

        except Exception as e:
            logger.error(f"[MatchSummaryModule] LLM generation failed: {e}")
            # 降级：返回原始数据摘要
            return self._fallback_summary(data, summary_type)

    def _get_system_prompt(self, summary_type: str) -> str:
        """根据总结类型获取system prompt"""

        base_prompt = """你是一个足球新闻编辑。

任务：将比赛或球队信息总结成简洁的摘要。

总体要求：
1. **简洁**：控制在150-200字
2. **要点清晰**：3-5个关键点
3. **客观**：基于数据，不主观评价
4. **结构化**：使用emoji和列表
"""

        type_specific = {
            "single_match": """
特定任务：单场比赛总结

输出格式：
⚽ 比赛总结：
- 比分/预测结果
- 关键时刻/数据
- 影响

控制在100-150字。
""",
            "team_period": """
特定任务：球队阶段总结

输出格式：
📊 球队总结：
- 近期战绩
- 核心数据（排名、胜率）
- 状态趋势

控制在100-150字。
""",
            "league_overview": """
特定任务：联赛概况

输出格式：
🏆 联赛概况：
- 领头羊
- 争冠形势
- 降级区

控制在150-200字。
"""
        }

        return base_prompt + type_specific.get(summary_type, "")

    def _extract_key_points(self, summary_text: str) -> List[str]:
        """
        从摘要中提取关键要点

        简单实现：提取列表项
        """
        key_points = []

        lines = summary_text.split('\n')
        for line in lines:
            line = line.strip()
            # 提取列表项（以 - 或 * 开头）
            if line.startswith('-') or line.startswith('*'):
                point = line.lstrip('- *').strip()
                if point:
                    key_points.append(point)

        return key_points[:5]  # 最多5个要点

    def _fallback_summary(self, data: str, summary_type: str) -> str:
        """降级总结（LLM不可用时）"""
        # 简单截取前500字符
        truncated = data[:500]

        summary = f"📝 数据摘要（{summary_type}）\n\n"
        summary += truncated

        if len(data) > 500:
            summary += "\n\n...（数据较长，已截取）"

        return summary
