"""
DataStatsAgent - 数据统计专家智能体

职责：
1. 处理与数据/状态/特征相关的查询
2. 调用 DataService 和 StatsService 获取信息
3. 返回结构化数据或自然语言描述

实现方式：
- 基于 LangChain AgentExecutor
- 使用 DataTool 和 StatsTool
- 不直接访问数据库，通过 Service 层
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from src.services.data_service import data_service
from src.services.stats_service import stats_service

if TYPE_CHECKING:
    from src.shared.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ==================== Tool Schemas ====================

class GetMatchesInput(BaseModel):
    """获取比赛列表的输入"""
    team_name: Optional[str] = Field(None, description="球队名称（可选）")
    competition: Optional[str] = Field(None, description="联赛名称（可选）")
    limit: int = Field(10, description="返回数量")


class GetTeamFormInput(BaseModel):
    """获取球队近况的输入"""
    team_name: str = Field(..., description="球队名称")
    last_n: int = Field(5, description="最近场次数")


class GetStandingsInput(BaseModel):
    """获取积分榜的输入"""
    competition: str = Field(..., description="联赛名称")


class GetH2HInput(BaseModel):
    """获取历史交锋的输入"""
    team_a: str = Field(..., description="球队A名称")
    team_b: str = Field(..., description="球队B名称")
    last_n: int = Field(5, description="最近场次数")


# ==================== DataStatsAgent ====================

class DataStatsAgent:
    """
    数据统计专家智能体
    
    擅长回答：
    - "曼联最近5场比赛战绩如何？"
    - "英超积分榜前5是谁？"
    - "阿森纳和曼城最近交锋记录？"
    - "利物浦主场表现怎么样？"
    """
    
    def __init__(self, llm_client: 'LLMClient'):
        """
        初始化数据统计专家
        
        Args:
            llm_client: LLM 客户端实例
        """
        self._llm_client = llm_client
        self._llm = llm_client.as_langchain_chat_model()
        
        # 创建工具
        self._tools = self._create_tools()
        
        # 创建 Prompt
        self._prompt = self._create_prompt()
        
        # 创建 Agent Executor
        self._agent_executor = self._create_agent_executor()
        
        logger.info(f"DataStatsAgent initialized with {len(self._tools)} tools")
    
    def _create_tools(self):
        """创建数据统计工具"""
        
        async def get_recent_matches(team_name: str, limit: int = 10) -> str:
            """获取球队最近比赛列表"""
            try:
                matches = await data_service.get_recent_matches(
                    team_name=team_name,
                    last_n=limit
                )
                
                if not matches:
                    return f"未找到 {team_name} 的比赛记录"
                
                # 格式化输出
                lines = [f"{team_name} 最近 {len(matches)} 场比赛：\n"]
                for m in matches:
                    home = m.home_team.name
                    away = m.away_team.name
                    score = f"{m.home_score}-{m.away_score}" if m.home_score is not None else "未开始"
                    date = m.match_date.strftime("%Y-%m-%d")
                    lines.append(f"- {date}: {home} vs {away} ({score})")
                
                return "\n".join(lines)
            except Exception as e:
                logger.error(f"get_recent_matches failed: {e}")
                return f"获取比赛数据失败：{str(e)}"
        
        async def get_team_form(team_name: str, last_n: int = 5) -> str:
            """获取球队近期状态统计"""
            try:
                form = await stats_service.get_team_form(
                    team_name=team_name,
                    last_n=last_n
                )
                
                if not form:
                    return f"未找到 {team_name} 的统计数据"
                
                return (
                    f"{form.team_name} 近 {form.matches_analyzed} 场战绩：\n"
                    f"- 胜/平/负: {form.wins}胜 {form.draws}平 {form.losses}负\n"
                    f"- 胜率: {form.win_rate:.1%}\n"
                    f"- 进球/失球: {form.goals_for}/{form.goals_against}\n"
                    f"- 净胜球: {form.goal_difference:+d}\n"
                    f"- 状态走势: {form.form_string}\n"
                    f"- 得分: {form.points} 分"
                )
            except Exception as e:
                logger.error(f"get_team_form failed: {e}")
                return f"获取球队状态失败：{str(e)}"
        
        async def get_standings(competition: str) -> str:
            """获取联赛积分榜"""
            try:
                standings = await data_service.get_standings(competition=competition)
                
                if not standings:
                    return f"未找到 {competition} 的积分榜数据"
                
                lines = [f"{competition} 积分榜（前10）：\n"]
                for s in standings[:10]:
                    lines.append(
                        f"{s.position}. {s.team.name} - "
                        f"{s.points}分 ({s.won}胜 {s.draw}平 {s.lost}负)"
                    )
                
                return "\n".join(lines)
            except Exception as e:
                logger.error(f"get_standings failed: {e}")
                return f"获取积分榜失败：{str(e)}"
        
        async def get_head_to_head(team_a: str, team_b: str, last_n: int = 5) -> str:
            """获取两队历史交锋记录"""
            try:
                h2h = await stats_service.get_head_to_head(
                    team_a_name=team_a,
                    team_b_name=team_b,
                    last_n=last_n
                )
                
                if not h2h:
                    return f"未找到 {team_a} 和 {team_b} 的交锋记录"
                
                return (
                    f"{h2h.team_a_name} vs {h2h.team_b_name} 历史交锋（近{h2h.total_matches}场）：\n"
                    f"- {h2h.team_a_name} {h2h.team_a_wins} 胜\n"
                    f"- 平局 {h2h.draws} 场\n"
                    f"- {h2h.team_b_name} {h2h.team_b_wins} 胜\n"
                    f"- 进球数: {h2h.team_a_goals} - {h2h.team_b_goals}\n"
                    f"- 最近5场: {', '.join(h2h.last_5_results)}"
                )
            except Exception as e:
                logger.error(f"get_head_to_head failed: {e}")
                return f"获取交锋记录失败：{str(e)}"
        
        async def get_home_away_stats(team_name: str, venue: str = "home") -> str:
            """获取主场或客场表现"""
            try:
                stats = await stats_service.get_home_away_stats(
                    team_name=team_name,
                    venue=venue,
                    last_n=10
                )
                
                if not stats:
                    return f"未找到 {team_name} 的{venue}场数据"
                
                venue_cn = "主" if venue == "home" else "客"
                return (
                    f"{stats.team_name} {venue_cn}场表现（近{stats.matches_analyzed}场）：\n"
                    f"- 胜/平/负: {stats.wins}胜 {stats.draws}平 {stats.losses}负\n"
                    f"- 胜率: {stats.win_rate:.1%}\n"
                    f"- 场均进球: {stats.avg_goals_for:.2f}\n"
                    f"- 场均失球: {stats.avg_goals_against:.2f}"
                )
            except Exception as e:
                logger.error(f"get_home_away_stats failed: {e}")
                return f"获取主客场数据失败：{str(e)}"
        
        # 使用 StructuredTool 包装
        tools = [
            StructuredTool.from_function(
                coroutine=get_recent_matches,
                name="get_recent_matches",
                description="获取球队最近的比赛列表和结果"
            ),
            StructuredTool.from_function(
                coroutine=get_team_form,
                name="get_team_form",
                description="获取球队近期状态统计（胜率、进球、失球等）"
            ),
            StructuredTool.from_function(
                coroutine=get_standings,
                name="get_standings",
                description="获取联赛积分榜排名"
            ),
            StructuredTool.from_function(
                coroutine=get_head_to_head,
                name="get_head_to_head",
                description="获取两队历史交锋记录和统计"
            ),
            StructuredTool.from_function(
                coroutine=get_home_away_stats,
                name="get_home_away_stats",
                description="获取球队主场或客场的表现统计"
            )
        ]
        
        return tools
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """创建 Agent Prompt"""
        system_message = """你是数据统计专家，擅长查询和分析足球比赛、球队的数据和统计信息。

你可以使用以下工具：
- get_recent_matches: 获取球队最近比赛记录
- get_team_form: 获取球队近期状态统计
- get_standings: 获取联赛积分榜
- get_head_to_head: 获取两队历史交锋
- get_home_away_stats: 获取主客场表现

工作要求：
1. 理解用户问题，选择合适的工具
2. 必要时组合多个工具获取完整信息
3. 用清晰、简洁的语言呈现数据
4. 如果无法获取数据，诚实告知

回答风格：
- 数据驱动，有理有据
- 突出关键数字和趋势
- 简洁明了，避免冗余
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return prompt
    
    def _create_agent_executor(self) -> AgentExecutor:
        """创建 Agent Executor"""
        agent = create_openai_functions_agent(
            llm=self._llm,
            tools=self._tools,
            prompt=self._prompt
        )
        
        executor = AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate",
            handle_parsing_errors=True
        )
        
        return executor
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        同步执行查询
        
        Args:
            query: 用户查询
            
        Returns:
            结果字典
        """
        try:
            result = self._agent_executor.invoke({"input": query})
            return {
                "output": result.get("output", ""),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"DataStatsAgent.run failed: {e}")
            return {
                "output": f"查询数据时出错：{str(e)}",
                "status": "error"
            }
    
    async def arun(self, query: str) -> Dict[str, Any]:
        """
        异步执行查询
        
        Args:
            query: 用户查询
            
        Returns:
            结果字典
        """
        try:
            result = await self._agent_executor.ainvoke({"input": query})
            return {
                "output": result.get("output", ""),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"DataStatsAgent.arun failed: {e}")
            return {
                "output": f"查询数据时出错：{str(e)}",
                "status": "error"
            }

