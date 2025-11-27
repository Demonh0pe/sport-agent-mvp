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

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from src.services.data_service import data_service
from src.services.stats_service import stats_service

if TYPE_CHECKING:
    from src.shared.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ==================== Tool Schemas ====================

class GetRecentMatchesInput(BaseModel):
    """获取球队最近比赛的输入参数"""
    team_name: str = Field(..., description="球队名称，支持中英文，如 'Manchester United' 或 '曼联'")
    match_count: int = Field(10, description="要查询的比赛数量，默认 10 场")


class GetTeamFormInput(BaseModel):
    """获取球队近况统计的输入参数"""
    team_name: str = Field(..., description="球队名称，支持中英文")
    last_n: int = Field(5, description="分析最近 N 场比赛，默认 5 场")


class GetStandingsInput(BaseModel):
    """获取联赛积分榜的输入参数"""
    competition: str = Field(..., description="联赛名称，如 'Premier League' 或 '英超'")
    team_name: Optional[str] = Field(None, description="可选：如果提供球队名，则返回该队的精确排名和积分信息")
    full_list: bool = Field(False, description="是否返回完整积分榜。注意：如果查询'最后一名'、'倒数第一'、'降级区'等，必须设为True")


class GetH2HInput(BaseModel):
    """获取历史交锋的输入参数"""
    team_a: str = Field(..., description="球队A名称")
    team_b: str = Field(..., description="球队B名称")
    last_n: int = Field(5, description="查询最近 N 场交锋，默认 5 场")


class GetHomeAwayStatsInput(BaseModel):
    """获取主客场统计的输入参数"""
    team_name: str = Field(..., description="球队名称")
    venue: str = Field("home", description="场地类型：'home'（主场）或 'away'（客场）")
    last_n: int = Field(10, description="分析最近 N 场比赛，默认 10 场")


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
        
        async def get_recent_matches(team_name: str, match_count: int = 10) -> str:
            """
            获取球队最近比赛列表
            
            Args:
                team_name: 球队名称，支持中英文
                match_count: 要查询的比赛数量
                
            Returns:
                格式化的比赛列表文本
            """
            try:
                matches = await data_service.get_recent_matches(
                    team_name=team_name,
                    last_n=match_count
                )
                
                if not matches:
                    return f"数据库中没有找到 {team_name} 的比赛记录"
                
                # 格式化输出
                lines = [f"{team_name} 最近 {len(matches)} 场比赛：\n"]
                for m in matches:
                    home = m.home_team.team_name if m.home_team else m.home_team_id
                    away = m.away_team.team_name if m.away_team else m.away_team_id
                    score = f"{m.home_score}-{m.away_score}" if m.home_score is not None else "未开始"
                    date = m.match_date.strftime("%Y-%m-%d")
                    lines.append(f"- {date}: {home} vs {away} ({score})")
                
                return "\n".join(lines)
            except Exception as e:
                logger.error(f"get_recent_matches failed: {e}", exc_info=True)
                return f"获取比赛数据失败：{str(e)}"
        
        async def get_team_form(team_name: str, last_n: int = 5) -> str:
            """
            获取球队近期状态统计
            
            Args:
                team_name: 球队名称
                last_n: 分析最近 N 场比赛
                
            Returns:
                格式化的球队状态统计文本
            """
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
        
        async def get_standings(
            competition: str, 
            team_name: Optional[str] = None, 
            full_list: bool = False
        ) -> str:
            """
            获取联赛积分榜
            
            Args:
                competition: 联赛名称
                team_name: 可选，如果提供则返回该队的精确排名
                full_list: 是否返回完整榜单（默认只返回前 10 名）
                
            Returns:
                格式化的积分榜文本
            """
            try:
                # 联赛名称映射（支持中英文）
                league_name_map = {
                    "英超": "Premier League",
                    "英格兰超级联赛": "Premier League",
                    "英超联赛": "Premier League",
                    "premier league": "Premier League",
                    "epl": "Premier League",
                    "德甲": "Bundesliga",
                    "西甲": "La Liga",
                    "意甲": "Serie A",
                    "法甲": "Ligue 1",
                    "欧冠": "Champions League",
                }
                
                # 标准化联赛名称
                normalized_competition = league_name_map.get(
                    competition.lower(), 
                    competition
                )
                
                standings = await data_service.get_standings(competition=normalized_competition)
                
                if not standings:
                    return f"未找到 {competition} 的积分榜数据"
                
                # 如果指定了 team_name，返回该队的精确排名
                if team_name:
                    # 模糊匹配队名
                    team_standing = None
                    for s in standings:
                        s_team_name = s.team_name if s.team_name else (s.team.team_name if s.team else s.team_id)
                        if team_name.lower() in s_team_name.lower() or s_team_name.lower() in team_name.lower():
                            team_standing = s
                            break
                    
                    if not team_standing:
                        return f"在 {competition} 积分榜中未找到 {team_name}"
                    
                    s = team_standing
                    s_team_name = s.team_name if s.team_name else (s.team.team_name if s.team else s.team_id)
                    return (
                        f"{s_team_name} 在 {competition} 中的排名：\n"
                        f"- 排名：第 {s.position} 位\n"
                        f"- 积分：{s.points} 分\n"
                        f"- 战绩：{s.won}胜 {s.draw}平 {s.lost}负\n"
                        f"- 进球/失球：{s.goals_for}/{s.goals_against}\n"
                        f"- 净胜球：{s.goal_difference:+d}"
                    )
                
                # 决定返回多少条记录
                if full_list:
                    display_standings = standings
                else:
                    display_standings = standings[:10]
                
                lines = [f"{competition} 积分榜（{'完整' if full_list else '前10'}）：\n"]
                for s in display_standings:
                    team_name_display = s.team_name if s.team_name else (s.team.team_name if s.team else s.team_id)
                    lines.append(
                        f"{s.position}. {team_name_display} - "
                        f"{s.points}分 ({s.won}胜 {s.draw}平 {s.lost}负)"
                    )
                
                return "\n".join(lines)
            except Exception as e:
                logger.error(f"get_standings failed: {e}")
                return f"获取积分榜失败：{str(e)}"
        
        async def get_head_to_head(team_a: str, team_b: str, last_n: int = 5) -> str:
            """
            获取两队历史交锋记录
            
            Args:
                team_a: 球队A名称
                team_b: 球队B名称
                last_n: 查询最近 N 场交锋
                
            Returns:
                格式化的历史交锋文本
            """
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
        
        async def get_home_away_stats(team_name: str, venue: str = "home", last_n: int = 10) -> str:
            """
            获取主场或客场表现
            
            Args:
                team_name: 球队名称
                venue: 场地类型，'home'（主场）或 'away'（客场）
                last_n: 分析最近 N 场比赛
                
            Returns:
                格式化的主客场统计文本
            """
            try:
                stats = await stats_service.get_home_away_stats(
                    team_name=team_name,
                    venue=venue,
                    last_n=last_n
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
        
        # 使用 StructuredTool 包装，并指定 args_schema
        tools = [
            StructuredTool.from_function(
                coroutine=get_recent_matches,
                name="get_recent_matches",
                description="获取球队最近的比赛列表和结果。适用于查询球队近期赛程、比分、胜负记录等。",
                args_schema=GetRecentMatchesInput
            ),
            StructuredTool.from_function(
                coroutine=get_team_form,
                name="get_team_form",
                description="获取球队近期状态统计（胜率、进球、失球、净胜球、状态走势等）。适用于分析球队近期表现。",
                args_schema=GetTeamFormInput
            ),
            StructuredTool.from_function(
                coroutine=get_standings,
                name="get_standings",
                description=(
                    "获取联赛积分榜排名。功能：\n"
                    "1. 如果只提供 competition，返回积分榜前10名\n"
                    "2. 如果提供 competition 和 team_name，返回该队的精确排名和积分\n"
                    "3. 如果 full_list=True，返回完整积分榜"
                ),
                args_schema=GetStandingsInput
            ),
            StructuredTool.from_function(
                coroutine=get_head_to_head,
                name="get_head_to_head",
                description="获取两队历史交锋记录和统计（胜负关系、进球数、最近交锋结果等）。",
                args_schema=GetH2HInput
            ),
            StructuredTool.from_function(
                coroutine=get_home_away_stats,
                name="get_home_away_stats",
                description="获取球队主场或客场的表现统计（胜率、场均进失球等）。适用于分析主客场优劣势。",
                args_schema=GetHomeAwayStatsInput
            )
        ]
        
        return tools
    
    def _create_prompt(self) -> PromptTemplate:
        """创建 Agent Prompt（ReAct 格式）"""
        template = """你是数据统计专家,负责查询和分析足球比赛数据。

可用工具：

{tools}

工具使用指南：
1. get_recent_matches: 查询球队近期比赛
   - 参数：team_name（球队名称），match_count（比赛数量）
   
2. get_team_form: 查询球队近期状态统计
   - 参数：team_name（球队名称），last_n（最近N场）
   
3. get_standings: 查询积分榜，有三种用法：
   - 只提供 competition：返回前10名
   - 提供 competition + team_name：返回该队精确排名（推荐用于"某队排第几"）
   - 提供 competition + full_list=True：返回完整榜单（当查询"最后一名"、"降级区"时必须使用）
   
4. get_head_to_head: 查询历史交锋
   - 参数：team_a、team_b（球队名称），last_n（最近N场）
   
5. get_home_away_stats: 查询主客场数据
   - 参数：team_name（球队名称），venue（home/away），last_n（最近N场）

重要规则：
- ✅ 工具返回什么就说什么，绝不编造数据
- ✅ 对于"某队排第几"的问题，使用 get_standings 的 team_name 参数
- ✅ 对于"最后一名"、"倒数第一"、"降级区"等问题，必须使用 full_list=True
- ✅ 支持中英文队名，如 "曼联" 或 "Manchester United"
- ✅ 联赛名称可用中文（"英超"）或英文（"Premier League"）
- ❌ 绝不使用占位符（XX、YY）
- ❌ 绝不假设或猜测数据
- ❌ 绝不从"前10名"数据中推测"最后一名"

使用以下格式回答：

Question: 用户的问题
Thought: 我需要做什么
Action: 工具名称
Action Input: {{"参数名": "参数值"}}
Observation: 工具返回结果
... (重复直到有答案)
Thought: 我现在知道最终答案了
Final Answer: 最终答案

可用工具名称：{tool_names}

开始！

Question: {input}
Thought: {agent_scratchpad}"""
        
        prompt = PromptTemplate.from_template(template)
        
        return prompt
    
    def _create_agent_executor(self) -> AgentExecutor:
        """创建 Agent Executor（使用 ReAct 模式,兼容本地LLM）"""
        agent = create_react_agent(
            llm=self._llm,
            tools=self._tools,
            prompt=self._prompt
        )
        
        executor = AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=True,
            max_iterations=10,  # 增加迭代次数,确保复杂查询能完成
            early_stopping_method="force",  # 使用 "force" 而不是已废弃的 "generate"
            handle_parsing_errors=True,
            return_intermediate_steps=True
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

