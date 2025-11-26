"""
赛事查询模块 (Match Query Module)

用户场景：
- "曼联最近5场比赛战绩"
- "利物浦在英超排名第几"
- "曼联对利物浦的历史交锋"
- "查询本周末有哪些比赛"

核心功能：
- 查询球队战绩
- 查询积分榜排名
- 查询历史交锋
- 查询比赛日程
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 导入现有工具
from src.agent.tools.match_tool import match_tool
from src.agent.tools.standings_tool import standings_tool
from src.agent.tools.stats_tool import stats_tool

# 导入LLM客户端（先用现有的，后期可以切换到v2）
from src.shared.llm_client import llm_client

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """查询结果"""
    query_type: str  # "recent_matches" / "standings" / "h2h" / "schedule"
    raw_data: str  # 原始数据
    formatted_text: str  # 格式化后的文本
    metadata: Dict[str, Any]  # 元数据


class MatchQueryModule:
    """
    赛事查询模块

    输入：用户查询 + 实体（球队、联赛、时间）
    输出：结构化数据 + 自然语言描述
    """

    def __init__(self):
        self.llm_enabled = True  # 是否使用LLM美化输出

    async def execute(self, query: str, entities: Dict[str, Any]) -> QueryResult:
        """
        执行查询

        Args:
            query: 用户原始查询
            entities: 提取的实体 {team, league, team_a, team_b, ...}

        Returns:
            QueryResult: 查询结果
        """
        logger.info(f"[MatchQueryModule] Processing query: {query}")
        logger.info(f"[MatchQueryModule] Entities: {entities}")

        # 1. 识别查询类型
        query_type = self._detect_query_type(query, entities)
        logger.info(f"[MatchQueryModule] Detected type: {query_type}")

        # 2. 调用对应工具获取数据
        raw_data, metadata = await self._fetch_data(query_type, entities)

        # 3. 用LLM美化输出（可选）
        if self.llm_enabled:
            formatted_text = await self._format_with_llm(query, raw_data, query_type)
        else:
            formatted_text = raw_data

        return QueryResult(
            query_type=query_type,
            raw_data=raw_data,
            formatted_text=formatted_text,
            metadata=metadata
        )

    def _detect_query_type(self, query: str, entities: Dict) -> str:
        """
        识别查询类型

        逻辑：
        - 关键词优先级：排名 > 历史交锋 > 战绩 > 日程
        - 如果有两个球队 → 历史交锋
        - 如果有"排名"、"积分榜" → 排名查询
        - 默认 → 战绩查询
        """
        query_lower = query.lower()

        # 历史交锋（两个球队）
        if 'team_b' in entities and entities.get('team_b'):
            if any(k in query_lower for k in ["交锋", "历史", "对阵", "vs", "对战"]):
                return "h2h"

        # 排名查询
        if any(k in query_lower for k in ["排名", "积分榜", "第几", "名次", "榜单"]):
            return "standings"

        # 日程查询
        if any(k in query_lower for k in ["日程", "赛程", "有哪些比赛", "本周", "今天"]):
            return "schedule"

        # 默认：战绩查询
        return "recent_matches"

    async def _fetch_data(
        self,
        query_type: str,
        entities: Dict
    ) -> tuple[str, Dict[str, Any]]:
        """
        根据查询类型获取数据

        Returns:
            (raw_data, metadata)
        """
        metadata = {"query_type": query_type}

        try:
            if query_type == "recent_matches":
                return await self._fetch_recent_matches(entities, metadata)

            elif query_type == "standings":
                return await self._fetch_standings(entities, metadata)

            elif query_type == "h2h":
                return await self._fetch_h2h(entities, metadata)

            elif query_type == "schedule":
                return await self._fetch_schedule(entities, metadata)

            else:
                return "未知的查询类型", metadata

        except Exception as e:
            logger.error(f"[MatchQueryModule] Fetch data failed: {e}", exc_info=True)
            return f"查询失败：{str(e)}", {"error": str(e)}

    async def _fetch_recent_matches(
        self,
        entities: Dict,
        metadata: Dict
    ) -> tuple[str, Dict]:
        """获取近期战绩"""
        team_name = entities.get('team') or entities.get('team_a')

        if not team_name:
            return "请指定球队名称", metadata

        # 调用match_tool
        result = await match_tool.get_recent_matches(
            team_name=team_name,
            limit=5
        )

        metadata['team'] = team_name
        metadata['limit'] = 5

        return result, metadata

    async def _fetch_standings(
        self,
        entities: Dict,
        metadata: Dict
    ) -> tuple[str, Dict]:
        """获取积分榜排名"""
        team_name = entities.get('team') or entities.get('team_a')
        league_name = entities.get('league')

        if not team_name:
            return "请指定球队名称", metadata

        # 调用standings_tool
        result = await standings_tool.get_team_standing(
            team_name=team_name
        )

        metadata['team'] = team_name
        metadata['league'] = league_name

        return result, metadata

    async def _fetch_h2h(
        self,
        entities: Dict,
        metadata: Dict
    ) -> tuple[str, Dict]:
        """获取历史交锋"""
        team_a = entities.get('team_a')
        team_b = entities.get('team_b')

        if not team_a or not team_b:
            return "请指定两个球队", metadata

        # 简单实现：分别查询两队战绩，然后组合
        # TODO: 后期可以添加专门的H2H工具
        result_a = await match_tool.get_recent_matches(team_a, limit=5)
        result_b = await match_tool.get_recent_matches(team_b, limit=5)

        combined_result = f"# {team_a} 近期战绩\n{result_a}\n\n# {team_b} 近期战绩\n{result_b}"

        metadata['team_a'] = team_a
        metadata['team_b'] = team_b

        return combined_result, metadata

    async def _fetch_schedule(
        self,
        entities: Dict,
        metadata: Dict
    ) -> tuple[str, Dict]:
        """获取比赛日程（暂时使用Mock数据）"""
        # TODO: 实现真实的日程查询
        return "比赛日程功能正在开发中...", metadata

    async def _format_with_llm(
        self,
        query: str,
        data: str,
        query_type: str
    ) -> str:
        """
        用LLM美化输出

        根据查询类型使用不同的prompt策略
        """
        system_prompt = self._get_system_prompt(query_type)
        user_prompt = f"""
用户问：{query}

查询数据：
{data}

请将数据格式化输出，要求：
1. 使用清晰的表格或列表
2. 突出关键信息（战绩、排名、胜率）
3. 简洁明了，不要冗长
4. 可以使用适当的emoji增强可读性
"""

        try:
            formatted = await llm_client.generate(system_prompt, user_prompt)
            return formatted

        except Exception as e:
            logger.error(f"[MatchQueryModule] LLM formatting failed: {e}")
            # 降级：直接返回原始数据
            return data

    def _get_system_prompt(self, query_type: str) -> str:
        """根据查询类型获取system prompt"""

        base_prompt = "你是一个专业的足球数据助手。"

        type_specific = {
            "recent_matches": """
任务：格式化球队近期战绩数据。

输出要求：
1. 使用表格展示比赛记录
2. 突出战绩统计（胜平负、胜率）
3. 标注近期走势（连胜、连败）
4. 简洁直观
""",
            "standings": """
任务：格式化积分榜数据。

输出要求：
1. 清晰展示排名、积分、战绩
2. 突出关键数据（胜率、净胜球）
3. 如果排名高，说明优势；排名低，说明劣势
4. 简洁客观
""",
            "h2h": """
任务：对比两支球队的近期状态。

输出要求：
1. 分别展示两队战绩
2. 对比关键数据（胜率、进球、失球）
3. 指出谁的状态更好
4. 简洁对比
""",
            "schedule": """
任务：展示比赛日程。

输出要求：
1. 按时间排序
2. 突出重要比赛
3. 简洁清晰
"""
        }

        return base_prompt + type_specific.get(query_type, "")

    def set_llm_enabled(self, enabled: bool):
        """开启/关闭LLM美化"""
        self.llm_enabled = enabled
