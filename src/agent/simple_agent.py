"""
SimpleAgent - 简化版足球赛事智能助手

功能：
1. 赛事查询 - 战绩、排名、历史交锋
2. 赛事分析 - 状态分析、对比、预测
3. 赛事总结 - 简洁摘要

设计理念：
- 简单规则优先（意图识别、实体提取）
- LLM负责生成和美化
- 模块化、易扩展
"""
from __future__ import annotations

import logging
from typing import Dict, Any
from dataclasses import dataclass

# 导入三个核心模块
from src.agent.modules.match_query import MatchQueryModule
from src.agent.modules.match_analysis import MatchAnalysisModule
from src.agent.modules.match_summary import MatchSummaryModule

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Agent响应"""
    answer: str  # 回答文本
    intent: str  # 识别的意图
    entities: Dict[str, Any]  # 提取的实体
    module_used: str  # 使用的模块
    metadata: Dict[str, Any] = None  # 元数据


class SimpleAgent:
    """
    简化版Agent

    只做3件事：
    1. 识别意图（查询/分析/总结）
    2. 提取实体（球队、联赛、时间）
    3. 路由到对应模块
    """

    def __init__(self):
        # 初始化三个模块
        self.query_module = MatchQueryModule()
        self.analysis_module = MatchAnalysisModule()
        self.summary_module = MatchSummaryModule()

        # 球队映射库
        self.team_map = self._init_team_map()

        # 联赛映射库
        self.league_map = self._init_league_map()

        logger.info("[SimpleAgent] Initialized with 3 modules")

    def _init_team_map(self) -> Dict[str, str]:
        """初始化球队映射库"""
        return {
            # 英超
            "曼联": "Manchester United",
            "manchester united": "Manchester United",
            "man utd": "Manchester United",
            "mun": "Manchester United",

            "利物浦": "Liverpool",
            "liverpool": "Liverpool",
            "liv": "Liverpool",

            "阿森纳": "Arsenal",
            "arsenal": "Arsenal",
            "ars": "Arsenal",

            "曼城": "Manchester City",
            "manchester city": "Manchester City",
            "man city": "Manchester City",
            "mci": "Manchester City",

            "切尔西": "Chelsea",
            "chelsea": "Chelsea",
            "che": "Chelsea",

            "热刺": "Tottenham Hotspur",
            "tottenham": "Tottenham Hotspur",
            "spurs": "Tottenham Hotspur",
            "tot": "Tottenham Hotspur",

            "纽卡": "Newcastle United",
            "纽卡斯尔": "Newcastle United",
            "newcastle": "Newcastle United",
            "new": "Newcastle United",

            "莱斯特": "Leicester City",
            "leicester": "Leicester City",
            "lei": "Leicester City",

            # 其他联赛
            "拜仁": "Bayern München",
            "拜仁慕尼黑": "Bayern München",
            "bayern": "Bayern München",
            "fcb": "Bayern München",

            "多特": "Borussia Dortmund",
            "多特蒙德": "Borussia Dortmund",
            "dortmund": "Borussia Dortmund",
            "bvb": "Borussia Dortmund",

            "皇马": "Real Madrid",
            "皇家马德里": "Real Madrid",
            "real madrid": "Real Madrid",
            "rma": "Real Madrid",

            "巴萨": "Barcelona",
            "巴塞罗那": "Barcelona",
            "barcelona": "Barcelona",
            "bar": "Barcelona",
            "barca": "Barcelona",
        }

    def _init_league_map(self) -> Dict[str, str]:
        """初始化联赛映射库"""
        return {
            "英超": "Premier League",
            "epl": "Premier League",
            "premier league": "Premier League",

            "西甲": "La Liga",
            "laliga": "La Liga",
            "la liga": "La Liga",

            "意甲": "Serie A",
            "serie a": "Serie A",

            "德甲": "Bundesliga",
            "bundesliga": "Bundesliga",

            "法甲": "Ligue 1",
            "ligue 1": "Ligue 1",
        }

    async def chat(self, user_input: str) -> AgentResponse:
        """
        主接口

        Args:
            user_input: 用户输入

        Returns:
            AgentResponse: Agent响应
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"[SimpleAgent] User input: {user_input}")
        logger.info(f"{'=' * 60}")

        try:
            # 1. 意图识别
            intent = self._classify_intent(user_input)
            logger.info(f"[SimpleAgent] Intent: {intent}")

            # 2. 实体提取
            entities = self._extract_entities(user_input)
            logger.info(f"[SimpleAgent] Entities: {entities}")

            # 3. 路由到对应模块
            if intent == "query":
                result = await self.query_module.execute(user_input, entities)
                answer = result.formatted_text
                module_used = "MatchQueryModule"

            elif intent == "analysis":
                result = await self.analysis_module.execute(user_input, entities)
                answer = result.analysis_text
                module_used = "MatchAnalysisModule"

            elif intent == "summary":
                result = await self.summary_module.execute(user_input, entities)
                answer = result.summary_text
                module_used = "MatchSummaryModule"

            else:
                answer = self._get_help_message()
                module_used = "Fallback"

            logger.info(f"[SimpleAgent] Module used: {module_used}")
            logger.info(f"[SimpleAgent] Answer generated (length: {len(answer)})")

            return AgentResponse(
                answer=answer,
                intent=intent,
                entities=entities,
                module_used=module_used,
                metadata={"result": result if 'result' in locals() else None}
            )

        except Exception as e:
            logger.error(f"[SimpleAgent] Error: {e}", exc_info=True)

            return AgentResponse(
                answer=f"抱歉，处理您的问题时出错了：{str(e)}",
                intent="error",
                entities={},
                module_used="Error",
                metadata={"error": str(e)}
            )

    def _classify_intent(self, query: str) -> str:
        """
        简单的意图识别（基于关键词）

        优先级：总结 > 分析 > 查询
        """
        query_lower = query.lower()

        # 总结关键词
        if any(k in query_lower for k in ["总结", "概述", "简要", "快速了解", "摘要"]):
            return "summary"

        # 分析关键词
        if any(k in query_lower for k in [
            "分析", "对比", "比较", "为什么", "怎么样", "如何",
            "预测", "谁会赢", "谁更强", "状态",
            "pk", "vs", "差距"
        ]):
            return "analysis"

        # 默认为查询
        return "query"

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """
        简单的实体提取（基于映射库）

        Returns:
            {
                team: 第一个球队（用于单队查询）
                team_a: 第一个球队（用于对比）
                team_b: 第二个球队（用于对比）
                league: 联赛
            }
        """
        entities = {}

        query_lower = query.lower()

        # 提取球队
        found_teams = []
        for cn_name, en_name in self.team_map.items():
            if cn_name in query or cn_name in query_lower:
                if en_name not in found_teams:  # 去重
                    found_teams.append(en_name)

        # 分配球队角色
        if len(found_teams) >= 1:
            entities['team'] = found_teams[0]
            entities['team_a'] = found_teams[0]

        if len(found_teams) >= 2:
            entities['team_b'] = found_teams[1]

        # 提取联赛
        for cn_name, en_name in self.league_map.items():
            if cn_name in query or cn_name in query_lower:
                entities['league'] = en_name
                break

        return entities

    def _get_help_message(self) -> str:
        """获取帮助信息"""
        return """抱歉，我不太理解您的问题。

您可以问我：

📊 **查询类**：
- 曼联最近5场比赛战绩
- 利物浦在英超排名第几
- 曼联对利物浦的历史交锋

🔍 **分析类**：
- 分析一下曼联最近的状态
- 曼联和利物浦谁更强
- 预测曼联对利物浦谁会赢

📝 **总结类**：
- 总结曼联最近的情况
- 简要说明利物浦的状态
"""


# 便捷函数
async def chat(user_input: str) -> str:
    """
    便捷的聊天函数

    Args:
        user_input: 用户输入

    Returns:
        回答文本
    """
    agent = SimpleAgent()
    response = await agent.chat(user_input)
    return response.answer
