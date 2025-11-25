"""
Agent Service
负责协调 Planner、Tools 和 LLM，处理用户请求的核心业务逻辑。
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

# 引入核心组件
from src.agent.core.planner import plan_decomposition
from src.services.api.schemas.agent import AgentQuery, AgentResponse, ToolInvocation
from src.shared.llm_client import llm_client
from src.agent.prompts.loader import PromptLoader
from src.agent.tools.match_tool import match_tool

if TYPE_CHECKING:
    from src.shared.config import Settings

# 配置日志
logger = logging.getLogger(__name__)

PLANNER_VERSION = "v1.2"


class AgentService:
    """Agent 协调服务类"""

    def __init__(self, settings: Settings):
        self._settings = settings
        # 默认开启 Trace，除非配置显式关闭
        self._enable_trace = getattr(settings.service.agent, "enable_trace", True)

    async def run_query(self, payload: AgentQuery) -> AgentResponse:
        """
        处理用户查询的主入口。
        
        流程:
        1. 输入预处理
        2. 规划 (Planner)
        3. 执行工具 (Tools)
        4. 生成回答 (LLM)
        5. 构造响应 (Response)
        """
        # 1. 归一化输入
        normalized_query = payload.query.strip()
        logger.info(f"Processing query: {normalized_query}")
        
        # 2. 调用规划器 (Planner)
        plan_steps = plan_decomposition(normalized_query)
        
        # 3. 执行工具链 (Execution Layer)
        # 注意: 目前 MVP 阶段主要处理 MatchResolverTool，后续将由 Executor 统一接管
        context_data = await self._execute_tools_manually(plan_steps, normalized_query)
        
        # 4. 调用 LLM 生成回答 (Generation Layer)
        try:
            # 渲染 Prompt 模板
            full_prompt = PromptLoader.render(
                "synthesis.jinja2",
                style="专业、客观、数据驱动",
                query=normalized_query,
                context_data=context_data
            )
            
            # 拆分 Prompt 并调用 LLM
            system_msg, user_msg = PromptLoader.split_role_content(full_prompt)
            llm_answer = await llm_client.generate(system_msg, user_msg)
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            llm_answer = "系统提示: 生成回答时遇到问题，请稍后重试。"

        # 5. 生成执行轨迹 (Trace)
        traces = self._build_traces(plan_steps, context_data)

        return AgentResponse(
            answer=llm_answer,
            reasoning=f"基于 {len(plan_steps)} 步规划，检索数据库并生成综述。",
            plan_steps=plan_steps,
            tool_traces=traces if self._enable_trace else [],
            planner_version=PLANNER_VERSION,
            generated_at=datetime.now(timezone.utc),
        )

    async def _execute_tools_manually(self, plan_steps: List[str], query: str) -> str:
        """
        手动执行工具逻辑 (MVP 阶段过渡方案)。
        
        Args:
            plan_steps: 规划步骤列表
            query: 原始查询字符串
            
        Returns:
            str: 聚合后的上下文数据文本
        """
        context_parts = []
        
        # 检查是否包含比赛查询意图
        # 这里的判断逻辑与 Planner 的输出保持一致
        steps_str = str(plan_steps)
        
        if "MatchResolverTool" in steps_str:
            # 简单的实体提取：常见球队名称模式匹配
            team_name = self._extract_team_name(query)
            
            if team_name:
                match_data = await match_tool.get_recent_matches(team_name=team_name)
                context_parts.append(match_data)
            else:
                context_parts.append("系统提示: 无法从查询中识别出球队名称。")
        
        if not context_parts:
            return "系统提示: 未触发本地数据查询，仅依据通用知识回答。"
            
        return "\n\n".join(context_parts)

    def _extract_team_name(self, query: str) -> str:
        """
        从查询中提取球队名称 (简单规则匹配)。
        后续将由专门的 Entity Recognition 模块替代。
        
        Args:
            query: 用户查询字符串
            
        Returns:
            str: 提取的球队名称，如果未找到则返回空字符串
        """
        # 常见球队名称列表 (中英文)
        known_teams = [
            "曼联", "Manchester United", "MUN",
            "利物浦", "Liverpool", "LIV",
            "阿森纳", "Arsenal", "ARS",
            "曼城", "Manchester City", "MCI",
            "切尔西", "Chelsea", "CHE",
            "巴萨", "Barcelona", "BAR",
            "皇马", "Real Madrid", "RMA",
        ]
        
        # 逐个匹配
        query_lower = query.lower()
        for team in known_teams:
            if team.lower() in query_lower:
                return team
                
        # 如果没有匹配到，尝试提取可能的球队名称 (前3个词)
        # 这是一个回退策略，不一定准确
        words = query.split()
        if words:
            return words[0]
            
        return ""

    def _build_traces(self, plan_steps: List[str], context_data: str) -> List[ToolInvocation]:
        """构建工具执行轨迹对象"""
        traces: List[ToolInvocation] = []
        
        for i, step in enumerate(plan_steps):
            # 简单的正则提取工具名
            match = re.match(r"([a-zA-Z]+Tool)", step.strip())
            tool_name = match.group(1) if match else "UnknownTool"
            
            # 如果是查询工具，且获取到了数据，则在 Trace 中展示部分数据
            snippet = "等待执行..."
            if tool_name == "MatchResolverTool":
                # 截取部分数据作为展示
                snippet = context_data[:100] + "..." if len(context_data) > 100 else context_data

            traces.append(
                ToolInvocation(
                    tool_name=tool_name,
                    input_payload={"raw_instruction": step},
                    output_snippet=snippet,
                    latency_ms=10 + (i * 5), # 暂保留模拟延迟
                )
            )
        return traces