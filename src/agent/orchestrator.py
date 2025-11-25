"""Agent 编排器：协调 Planner -> Executor -> Reasoner 的完整流程"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from src.agent.core.planner import plan_decomposition
from src.agent.core.executor import Executor
from src.agent.tools.mock_responses import MockToolResponses

if TYPE_CHECKING:
    from src.shared.config import Settings


class AgentOrchestrator:
    """
    Agent 的大脑协调器

    职责：
    1. 调用 Planner 生成工具链
    2. 调用 Executor 执行工具
    3. 整合结果并准备最终响应

    流程：
    用户查询 → Planner (生成计划) → Executor (执行工具) → 结果整合
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.mock_responses = MockToolResponses()

    async def orchestrate(
        self,
        query: str,
        user_id: Optional[str] = None,
        preferred_phase: str = "T-24h",
    ) -> dict:
        """
        协调整个 Agent 流程

        Args:
            query: 用户自然语言查询
            user_id: 用户 ID（用于日志和偏好跟踪）
            preferred_phase: 预测时点

        Returns:
            {
                "query": "...",
                "plan_steps": [...],
                "execution_result": {...},
                "answer": "...",
                ...
            }
        """
        # 1. Planner: 生成计划
        plan_steps = plan_decomposition(query)

        # 2. Executor: 执行工具（目前使用 Mock）
        execution_result = await self._execute_tools(plan_steps)

        # 3. 结果整合
        answer = self._build_answer(query, execution_result)

        return {
            "query": query,
            "user_id": user_id,
            "plan_steps": plan_steps,
            "execution_result": execution_result,
            "answer": answer,
            "status": "success",
        }

    async def _execute_tools(self, plan_steps: list) -> dict:
        """
        执行工具链

        当前实现：Mock 工具响应
        未来实现：真实 HTTP 调用
        """
        results = {}

        for step in plan_steps:
            # 从步骤字符串提取工具名
            tool_name = self._extract_tool_name(step)

            # 调用对应的 Mock 方法
            try:
                result = self._invoke_mock_tool(tool_name, step)
                results[tool_name] = result
            except Exception as e:
                results[tool_name] = {"error": str(e)}

        return {
            "tools_executed": list(results.keys()),
            "results": results,
            "total_latency_ms": sum(
                self._get_mock_latency(name) for name in results
            ),
        }

    def _extract_tool_name(self, step: str) -> str:
        """从步骤字符串提取工具名"""
        import re
        match = re.match(r"([a-zA-Z]+Tool)", step.strip())
        return match.group(1) if match else "UnknownTool"

    def _invoke_mock_tool(self, tool_name: str, step: str) -> dict:
        """调用 Mock 工具并返回响应"""
        # 提取参数（简化版）
        import re
        params_match = re.search(r"\((.*)\)$", step)
        params_str = params_match.group(1) if params_match else ""

        # 根据工具名调用相应的 Mock 方法
        if tool_name == "MatchResolverTool":
            result = self.mock_responses.match_resolver(
                query=self._extract_param(params_str, "query") or "Barcelona next match"
            )
        elif tool_name == "PredictionTool":
            result = self.mock_responses.prediction(
                match_id=self._extract_param(params_str, "match_id") or "test_match",
                phase=self._extract_param(params_str, "phase") or "T-24h",
            )
        elif tool_name == "NewsTool":
            result = self.mock_responses.news(
                entity_id=self._extract_param(params_str, "entity_id") or "Barcelona",
                entity_type=self._extract_param(params_str, "entity_type") or "team",
                window_hours=int(self._extract_param(params_str, "window_hours") or "72"),
            )
        elif tool_name == "StatsAnalysisTool":
            result = self.mock_responses.stats_analysis(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "HistoricalComparisonTool":
            result = self.mock_responses.historical_comparison(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "TacticalInsightTool":
            result = self.mock_responses.tactical_insight(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "LiveFeedTool":
            result = self.mock_responses.live_feed(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "PostMatchReviewTool":
            result = self.mock_responses.post_match_review(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "ScorelinePredictorTool":
            result = self.mock_responses.scoreline_predictor(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "EventPredictorTool":
            result = self.mock_responses.event_predictor(
                match_id=self._extract_param(params_str, "match_id") or "test_match",
                event_type=self._extract_param(params_str, "event_type") or "goals",
            )
        elif tool_name == "OddsTool":
            result = self.mock_responses.odds(
                match_id=self._extract_param(params_str, "match_id") or "test_match"
            )
        elif tool_name == "LLMAugmentorTool":
            result = self.mock_responses.llm_augmentor(
                context=self._extract_param(params_str, "context") or "test context"
            )
        elif tool_name == "StrategyTool":
            result = self.mock_responses.strategy(
                preference=self._extract_param(params_str, "preference") or "balanced"
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return result.model_dump() if hasattr(result, "model_dump") else result

    @staticmethod
    def _extract_param(params_str: str, param_name: str) -> Optional[str]:
        """从参数字符串提取单个参数的值"""
        import re
        pattern = rf"{param_name}\s*=\s*['\"]?([^,'\"\)]+)['\"]?"
        match = re.search(pattern, params_str)
        return match.group(1) if match else None

    @staticmethod
    def _get_mock_latency(tool_name: str) -> int:
        """获取 Mock 工具的模拟延迟 (毫秒)"""
        # 不同工具的延迟不同，模拟真实场景
        latencies = {
            "MatchResolverTool": 50,
            "PredictionTool": 100,
            "NewsTool": 150,
            "StatsAnalysisTool": 80,
            "OddsTool": 120,
            "LLMAugmentorTool": 200,
        }
        return latencies.get(tool_name, 100)

    def _build_answer(self, query: str, execution_result: dict) -> str:
        """从执行结果构建自然语言答案"""
        tools_executed = execution_result.get("tools_executed", [])

        if not tools_executed:
            return "未能找到合适的工具来回答您的问题。"

        answer = (
            f"我已经为您的问题 \"{query}\" 调用了 {len(tools_executed)} 个分析工具。\n"
            f"使用的工具：{', '.join(tools_executed)}\n\n"
            "执行结果摘要：\n"
        )

        # 基于执行的工具类型生成答案
        results = execution_result.get("results", {})

        if "PredictionTool" in tools_executed and "PredictionTool" in results:
            pred = results["PredictionTool"]
            answer += (
                f"• 胜平负预测：主胜 {pred.get('home_win', 0):.1%}, "
                f"平局 {pred.get('draw', 0):.1%}, "
                f"客胜 {pred.get('away_win', 0):.1%}\n"
            )

        if "NewsTool" in tools_executed and "NewsTool" in results:
            news = results["NewsTool"]
            items = news.get("items", [])
            answer += f"• 最新资讯：获取了 {len(items)} 条相关新闻\n"
            if items and isinstance(items, list) and len(items) > 0:
                answer += f"  - {items[0].get('title') if isinstance(items[0], dict) else 'News item'}\n"

        if "HistoricalComparisonTool" in tools_executed and "HistoricalComparisonTool" in results:
            hist = results["HistoricalComparisonTool"]
            answer += f"• 历史对比：{hist.get('h2h_summary', '无法获取')}\n"

        if "OddsTool" in tools_executed and "OddsTool" in results:
            odds = results["OddsTool"]
            answer += f"• 赔率信息：已获取主流博彩公司盘口\n"

        answer += (
            f"\n（当前为 Day 1 Mock 模式，工具返回伪数据供测试之用。"
            f"执行耗时 {execution_result.get('total_latency_ms', 0)} ms）"
        )

        return answer
