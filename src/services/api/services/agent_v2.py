"""
Agent Service v2.0 - 统一架构版本

主要改进：
1. 使用 AgentOrchestrator 统一工具调度
2. 支持真实工具和 Mock 工具混合使用
3. 改进的工具执行追踪
4. 更好的错误处理和日志
5. 支持异步 LLM 生成
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, TYPE_CHECKING

# 核心组件
from src.agent.core.planner import plan_decomposition
from src.agent.core.parameter_resolver import ParameterResolver
from src.services.api.schemas.agent import AgentQuery, AgentResponse, ToolInvocation
from src.shared.llm_client import llm_client
from src.agent.prompts.loader import PromptLoader

# 真实工具
from src.agent.tools.match_tool import match_tool
from src.agent.tools.stats_tool import stats_tool
from src.agent.tools.standings_tool import standings_tool
from src.agent.tools.prediction_tool import prediction_tool

# Mock 工具
from src.agent.tools.mock_responses import MockToolResponses

# 实体解析器
from src.data_pipeline.entity_resolver import entity_resolver

if TYPE_CHECKING:
    from src.shared.config import Settings

# 配置日志
logger = logging.getLogger(__name__)

PLANNER_VERSION = "v2.0"


class AgentServiceV2:
    """
    Agent 服务 v2.0 - 统一架构
    
    设计理念：
    - Planner: 意图识别 + 工具链规划
    - ParameterResolver: 参数解析与绑定
    - Executor: 工具执行（真实 + Mock 混合）
    - LLM Generator: 自然语言生成
    """
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._enable_trace = getattr(settings.service.agent, "enable_trace", True)
        
        # 初始化组件
        self._parameter_resolver = ParameterResolver()
        self._mock_responses = MockToolResponses()
        self._entity_resolver = entity_resolver
        self._entity_resolver_initialized = False
        
        # 工具注册表：哪些工具已实现真实数据
        self._real_tools = {
            "MatchResolverTool": match_tool.get_recent_matches,
            "StatsAnalysisTool": stats_tool.get_team_stats,
            "StandingsTool": standings_tool.get_team_standing,
            "PredictionTool": prediction_tool.predict_match,  # ✅ 新增预测工具
            # 后续添加：
            # "NewsTool": news_tool.search_news,
        }
        
        logger.info(f"AgentServiceV2 initialized with {len(self._real_tools)} real tools")
    
    async def _ensure_entity_resolver_initialized(self):
        """确保EntityResolver已初始化"""
        if not self._entity_resolver_initialized:
            await self._entity_resolver.initialize()
            self._entity_resolver_initialized = True
    
    async def run_query(self, payload: AgentQuery) -> AgentResponse:
        """
        处理用户查询的主入口
        
        流程：
        1. 输入预处理
        2. 规划 (Planner)
        3. 参数解析 (ParameterResolver)
        4. 执行工具 (Real + Mock Executor)
        5. LLM 生成回答
        6. 构造响应
        """
        start_time = datetime.now()
        normalized_query = payload.query.strip()
        
        # 确保EntityResolver已初始化
        await self._ensure_entity_resolver_initialized()
        
        logger.info(f"[V2] Processing query: {normalized_query}")
        
        try:
            # 1. 规划：生成工具链
            plan_steps = plan_decomposition(normalized_query)
            logger.info(f"[V2] Generated plan: {plan_steps}")
            
            # 2. 参数解析
            parsed_steps = []
            for step in plan_steps:
                try:
                    parsed = self._parameter_resolver.parse_step(step)
                    parsed_steps.append(parsed)
                except Exception as e:
                    logger.warning(f"Failed to parse step '{step}': {e}")
                    continue
            
            # 3. 执行工具链（智能路由：真实工具 vs Mock）
            execution_context = {"query": normalized_query}
            tool_results = await self._execute_tools(
                parsed_steps, 
                execution_context
            )
            
            # 4. 聚合上下文数据
            context_data = self._aggregate_tool_results(tool_results)
            
            # 5. LLM 生成回答
            llm_answer = await self._generate_answer(
                query=normalized_query,
                context_data=context_data,
                tool_results=tool_results
            )
            
            # 6. 构造执行轨迹
            traces = self._build_execution_traces(
                parsed_steps, 
                tool_results
            )
            
            # 计算总耗时
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return AgentResponse(
                answer=llm_answer,
                reasoning=f"基于 {len(plan_steps)} 步规划，使用了 {len(tool_results)} 个工具。",
                plan_steps=plan_steps,
                tool_traces=traces if self._enable_trace else [],
                planner_version=PLANNER_VERSION,
                generated_at=datetime.now(timezone.utc),
            )
            
        except Exception as e:
            logger.error(f"[V2] Query processing failed: {e}", exc_info=True)
            return AgentResponse(
                answer=f"系统错误：{str(e)}。请稍后重试。",
                reasoning="执行过程中遇到异常",
                plan_steps=[],
                tool_traces=[],
                planner_version=PLANNER_VERSION,
                generated_at=datetime.now(timezone.utc),
            )
    
    async def _execute_tools(
        self, 
        parsed_steps: List[Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        执行工具链（智能路由）
        
        策略：
        1. 检查工具是否有真实实现
        2. 有则调用真实工具
        3. 无则使用 Mock 数据
        """
        results = []
        
        for parsed_step in parsed_steps:
            tool_name = parsed_step.tool_name
            
            try:
                start_time = datetime.now()
                
                # 路由决策：真实工具 or Mock
                if tool_name in self._real_tools:
                    logger.info(f"[V2] Executing REAL tool: {tool_name}")
                    result = await self._execute_real_tool(
                        tool_name, 
                        parsed_step, 
                        context
                    )
                    source = "real"
                else:
                    logger.info(f"[V2] Executing MOCK tool: {tool_name}")
                    result = self._execute_mock_tool(
                        tool_name, 
                        parsed_step
                    )
                    source = "mock"
                
                # 计算耗时
                latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                results.append({
                    "tool_name": tool_name,
                    "status": "success",
                    "source": source,  # real / mock
                    "output": result,
                    "latency_ms": latency_ms,
                    "input_params": parsed_step.raw_params
                })
                
                # 更新上下文（用于后续工具的占位符填充）
                if tool_name == "MatchResolverTool" and isinstance(result, str):
                    # 从输出中提取 match_id（简化版）
                    context["match_id"] = "extracted_match_id"
                
            except Exception as e:
                logger.error(f"[V2] Tool {tool_name} execution failed: {e}")
                results.append({
                    "tool_name": tool_name,
                    "status": "error",
                    "source": "unknown",
                    "output": f"执行失败: {str(e)}",
                    "latency_ms": 0,
                    "input_params": parsed_step.raw_params
                })
        
        return results
    
    async def _execute_real_tool(
        self,
        tool_name: str,
        parsed_step: Any,
        context: Dict[str, Any]
    ) -> Any:
        """执行真实工具"""
        tool_func = self._real_tools[tool_name]
        
        # 根据工具类型调用
        if tool_name == "MatchResolverTool":
            # 从查询或参数中提取 team_name
            team_name = parsed_step.raw_params.get("query") or context.get("query", "")
            # 使用实体提取逻辑
            team_name = await self._extract_team_name(team_name)
            
            if not team_name:
                return "系统提示: 无法识别球队名称。"
            
            # 调用真实工具
            result = await tool_func(team_name=team_name)
            return result
        
        elif tool_name == "StatsAnalysisTool":
            # 从参数中提取 team_id 或 从上下文/查询中提取
            team_name = (
                parsed_step.raw_params.get("team_id") or 
                parsed_step.raw_params.get("match_id") or  # 从 match_id 提取
                context.get("query", "")
            )
            team_name = await self._extract_team_name(team_name)
            
            if not team_name:
                return "系统提示: 无法识别球队名称。"
            
            # 获取参数
            last_n = int(parsed_step.raw_params.get("last_n", 10))
            venue = parsed_step.raw_params.get("venue")
            
            # 调用真实工具
            result = await tool_func(
                team_name=team_name,
                last_n=last_n,
                venue=venue
            )
            return result
        
        elif tool_name == "StandingsTool":
            # 从参数或查询中提取球队名称和联赛名称
            team_name = (
                parsed_step.raw_params.get("team_name") or 
                await self._extract_team_name(context.get("query", ""))
            )
            league_name = parsed_step.raw_params.get("league_name")
            
            if not team_name:
                return "系统提示: 无法识别球队名称。"
            
            # 调用真实工具
            result = await tool_func(
                team_name=team_name,
                league_name=league_name
            )
            return result
        
        elif tool_name == "PredictionTool":
            # 从参数或查询中提取主队和客队名称
            query_text = context.get("query", "")
            
            # 尝试从参数获取
            home_team = parsed_step.raw_params.get("home_team")
            away_team = parsed_step.raw_params.get("away_team")
            league_name = parsed_step.raw_params.get("league")
            
            # 如果参数中没有，尝试从查询中解析
            if not home_team or not away_team:
                teams = await self._extract_two_teams(query_text)
                if teams:
                    home_team, away_team = teams
            
            if not home_team or not away_team:
                return "系统提示: 无法识别比赛双方球队，请明确指出主队和客队。"
            
            # 调用预测工具
            result = await tool_func(
                home_team_name=home_team,
                away_team_name=away_team,
                league_name=league_name
            )
            return result
        
        else:
            # 其他真实工具的调用逻辑
            return await tool_func(**parsed_step.raw_params)
    
    def _execute_mock_tool(self, tool_name: str, parsed_step: Any) -> Any:
        """执行 Mock 工具"""
        params = parsed_step.raw_params
        
        # 根据工具名调用相应的 Mock 方法
        if tool_name == "PredictionTool":
            return self._mock_responses.prediction(
                match_id=params.get("match_id", "test_match"),
                phase=params.get("phase", "T-24h")
            ).model_dump()
        
        elif tool_name == "NewsTool":
            return self._mock_responses.news(
                entity_id=params.get("entity_id", "test_team"),
                entity_type=params.get("entity_type", "team"),
                window_hours=int(params.get("window_hours", 72))
            ).model_dump()
        
        elif tool_name == "StatsAnalysisTool":
            return self._mock_responses.stats_analysis(
                match_id=params.get("match_id", "test_match")
            ).model_dump()
        
        elif tool_name == "HistoricalComparisonTool":
            return self._mock_responses.historical_comparison(
                match_id=params.get("match_id", "test_match")
            ).model_dump()
        
        elif tool_name == "LLMAugmentorTool":
            return self._mock_responses.llm_augmentor(
                context=params.get("context", "test_context")
            ).model_dump()
        
        else:
            return {"error": f"Unknown mock tool: {tool_name}"}
    
    def _aggregate_tool_results(self, tool_results: List[Dict]) -> str:
        """聚合工具执行结果为上下文文本"""
        context_parts = []
        
        for result in tool_results:
            if result["status"] == "success":
                output = result["output"]
                
                # 根据数据类型格式化
                if isinstance(output, str):
                    context_parts.append(output)
                elif isinstance(output, dict):
                    # Mock 数据格式化
                    tool_name = result["tool_name"]
                    context_parts.append(f"\n【{tool_name} 结果】\n{self._format_dict_output(output)}")
        
        return "\n\n".join(context_parts) if context_parts else "无可用数据"
    
    def _format_dict_output(self, data: dict) -> str:
        """格式化字典输出为可读文本"""
        lines = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                lines.append(f"- {key}: {len(value) if isinstance(value, list) else 'nested'} 项")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    async def _generate_answer(
        self,
        query: str,
        context_data: str,
        tool_results: List[Dict]
    ) -> str:
        """使用 LLM 生成最终回答"""
        try:
            # 检查是否有有效数据
            has_real_data = any(
                r["status"] == "success" and r["source"] == "real" 
                for r in tool_results
            )
            
            # 渲染 Prompt
            full_prompt = PromptLoader.render(
                "synthesis.jinja2",
                style="专业、客观、数据驱动",
                query=query,
                context_data=context_data
            )
            
            # 调用 LLM
            system_msg, user_msg = PromptLoader.split_role_content(full_prompt)
            llm_answer = await llm_client.generate(system_msg, user_msg)
            
            # 如果使用了 Mock 数据，添加提示
            if not has_real_data and any(r["source"] == "mock" for r in tool_results):
                llm_answer += "\n\n（注：部分数据为演示数据）"
            
            return llm_answer
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"根据您的查询，系统获取了相关数据，但生成回答时遇到问题。原始数据：\n\n{context_data}"
    
    def _build_execution_traces(
        self,
        parsed_steps: List[Any],
        tool_results: List[Dict]
    ) -> List[ToolInvocation]:
        """构建执行轨迹"""
        traces = []
        
        for i, result in enumerate(tool_results):
            # 获取输出片段
            output = result["output"]
            if isinstance(output, str):
                snippet = output[:150] + "..." if len(output) > 150 else output
            else:
                snippet = f"返回 {len(output)} 项数据" if isinstance(output, (list, dict)) else str(output)
            
            traces.append(
                ToolInvocation(
                    tool_name=result["tool_name"],
                    input_payload=result["input_params"],
                    output_snippet=snippet,
                    latency_ms=result["latency_ms"]
                )
            )
        
        return traces
    
    async def _extract_team_name(self, query: str) -> str:
        """
        从查询中提取球队名称（使用EntityResolver）
        
        策略：
        1. 将查询按空格和标点分词
        2. 尝试解析每个词为球队
        3. 返回第一个匹配的球队名称
        """
        if not query:
            return ""
        
        # 清理查询字符串（去除引号、空格等）
        import re
        query = query.strip().strip("'\"")
        
        # 简单分词：按空格、标点分割
        words = re.split(r'[\s,，、。！？：；]+', query)
        
        # 尝试解析每个词，使用更宽松的阈值
        for word in words:
            word = word.strip().strip("'\"")  # 清理每个词的引号
            if len(word) < 2:  # 跳过太短的词
                continue
            
            try:
                # 使用更低的阈值（0.6）来匹配更多球队
                team_id = await self._entity_resolver.resolve_team(
                    word, source="agent_v2", fuzzy_threshold=0.6
                )
                if team_id:
                    # 返回标准化的球队名称
                    team_info = await self._entity_resolver.get_team_info(team_id)
                    if team_info:
                        logger.info(f"成功识别球队: '{word}' -> {team_id} ({team_info['name']})")
                        return team_info["name"]
            except Exception as e:
                logger.debug(f"Failed to resolve word '{word}': {e}")
                continue
        
        return ""
    
    async def _extract_two_teams(self, query: str) -> tuple:
        """
        从查询中提取两个球队名称（使用EntityResolver）
        用于预测查询，如 "曼联对利物浦"
        
        Returns:
            (home_team, away_team) 或 None
        """
        if not query:
            return None
        
        # 清理查询字符串
        import re
        query = query.strip().strip("'\"")
        
        # 简单分词：按空格、标点分割
        words = re.split(r'[\s,，、。！？：；]+', query)
        
        # 尝试解析球队
        found_teams = []
        found_team_ids = set()  # 去重
        
        for word in words:
            word = word.strip().strip("'\"")  # 清理每个词的引号
            if len(word) < 2:  # 跳过太短的词
                continue
            
            try:
                # 使用更低的阈值（0.6）来匹配更多球队
                team_id = await self._entity_resolver.resolve_team(
                    word, source="agent_v2", fuzzy_threshold=0.6
                )
                if team_id and team_id not in found_team_ids:
                    team_info = await self._entity_resolver.get_team_info(team_id)
                    if team_info:
                        found_teams.append(team_info["name"])
                        found_team_ids.add(team_id)
                        logger.info(f"成功识别球队: '{word}' -> {team_id} ({team_info['name']})")
                        
                        # 找到两个球队就停止
                        if len(found_teams) >= 2:
                            break
            except Exception as e:
                logger.debug(f"Failed to resolve word '{word}': {e}")
                continue
        
        if len(found_teams) >= 2:
            return (found_teams[0], found_teams[1])
        
        return None

