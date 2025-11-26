"""
赛事分析模块 (Match Analysis Module)

用户场景：
- "分析一下曼联最近的状态"
- "曼联和利物浦谁更强？"
- "为什么利物浦排名第一？"
- "曼联对利物浦谁会赢？"

核心功能：
- 球队状态分析
- 两队对比分析
- 排名原因分析
- 比赛预测分析

使用已创建的：
- DataAnalyzer: 数据提取和对比
- ReasoningEngine: 深度推理
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# 导入核心组件
from src.agent.core.data_analyzer import DataAnalyzer
from src.agent.core.reasoning_engine import ReasoningEngine

# 导入现有工具
from src.agent.tools.match_tool import match_tool
from src.agent.tools.standings_tool import standings_tool
from src.agent.tools.stats_tool import stats_tool
from src.agent.tools.prediction_tool import prediction_tool

# 导入LLM客户端
from src.shared.llm_client import llm_client

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: str  # "team_status" / "comparison" / "prediction" / "ranking_reason"
    analysis_text: str  # 自然语言分析
    structured_data: Optional[Dict[str, Any]] = None  # 结构化数据
    reasoning: Optional[Any] = None  # 推理结果
    metadata: Dict[str, Any] = None  # 元数据


class MatchAnalysisModule:
    """
    赛事分析模块

    特点：深度分析，不仅给数据，还要解释为什么
    """

    def __init__(self):
        self.data_analyzer = DataAnalyzer()
        self.reasoning_engine = ReasoningEngine()

    async def execute(self, query: str, entities: Dict[str, Any]) -> AnalysisResult:
        """
        执行分析

        Args:
            query: 用户原始查询
            entities: 提取的实体

        Returns:
            AnalysisResult: 分析结果
        """
        logger.info(f"[MatchAnalysisModule] Processing query: {query}")
        logger.info(f"[MatchAnalysisModule] Entities: {entities}")

        # 1. 识别分析类型
        analysis_type = self._detect_analysis_type(query, entities)
        logger.info(f"[MatchAnalysisModule] Analysis type: {analysis_type}")

        # 2. 收集数据
        tool_results = await self._collect_data(entities, analysis_type)

        # 3. 数据分析（结构化）
        structured_data = self.data_analyzer.extract_structured_data(tool_results)

        # 4. 深度推理（如果是对比或预测）
        reasoning_result = None
        if analysis_type in ["comparison", "prediction"]:
            reasoning_result = await self._perform_reasoning(
                query,
                structured_data,
                analysis_type
            )

        # 5. 用LLM生成自然语言分析
        analysis_text = await self._generate_analysis(
            query,
            structured_data,
            reasoning_result,
            analysis_type
        )

        return AnalysisResult(
            analysis_type=analysis_type,
            analysis_text=analysis_text,
            structured_data=structured_data,
            reasoning=reasoning_result,
            metadata={"query": query, "entities": entities}
        )

    def _detect_analysis_type(self, query: str, entities: Dict) -> str:
        """
        识别分析类型

        优先级：
        1. 预测（谁会赢） > 对比 > 状态分析 > 排名原因
        """
        query_lower = query.lower()

        # 预测分析
        if any(k in query_lower for k in [
            "谁会赢", "谁会获胜", "预测", "会赢吗", "能赢吗",
            "概率", "胜算"
        ]):
            return "prediction"

        # 对比分析（两个球队）
        if 'team_b' in entities and entities.get('team_b'):
            if any(k in query_lower for k in [
                "对比", "比较", "谁更强", "谁更好", "差距",
                "vs", "pk", "哪个"
            ]):
                return "comparison"

        # 排名原因分析
        if any(k in query_lower for k in ["为什么", "原因", "怎么回事"]):
            if any(k in query_lower for k in ["排名", "第一", "这么高", "这么低"]):
                return "ranking_reason"

        # 默认：球队状态分析
        return "team_status"

    async def _collect_data(
        self,
        entities: Dict,
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """
        收集分析所需的数据

        Returns:
            工具结果列表
        """
        tool_results = []

        try:
            if analysis_type == "team_status":
                # 单个球队：战绩 + 排名
                team = entities.get('team') or entities.get('team_a')
                if team:
                    # 战绩
                    stats_result = await stats_tool.get_team_stats(team, last_n=10)
                    tool_results.append({
                        "tool_name": "StatsAnalysisTool",
                        "status": "success",
                        "source": "real",
                        "output": stats_result
                    })

                    # 排名
                    standing_result = await standings_tool.get_team_standing(team)
                    tool_results.append({
                        "tool_name": "StandingsTool",
                        "status": "success",
                        "source": "real",
                        "output": standing_result
                    })

            elif analysis_type in ["comparison", "prediction"]:
                # 两个球队：各自的战绩 + 排名
                team_a = entities.get('team_a') or entities.get('team')
                team_b = entities.get('team_b')

                if team_a:
                    stats_a = await stats_tool.get_team_stats(team_a, last_n=10)
                    standing_a = await standings_tool.get_team_standing(team_a)

                    tool_results.append({
                        "tool_name": "StatsAnalysisTool",
                        "status": "success",
                        "source": "real",
                        "output": stats_a
                    })
                    tool_results.append({
                        "tool_name": "StandingsTool",
                        "status": "success",
                        "source": "real",
                        "output": standing_a
                    })

                if team_b:
                    stats_b = await stats_tool.get_team_stats(team_b, last_n=10)
                    standing_b = await standings_tool.get_team_standing(team_b)

                    tool_results.append({
                        "tool_name": "StatsAnalysisTool",
                        "status": "success",
                        "source": "real",
                        "output": stats_b
                    })
                    tool_results.append({
                        "tool_name": "StandingsTool",
                        "status": "success",
                        "source": "real",
                        "output": standing_b
                    })

                # 如果是预测，调用预测工具
                if analysis_type == "prediction" and team_a and team_b:
                    try:
                        pred_result = await prediction_tool.predict_match(
                            home_team_name=team_a,
                            away_team_name=team_b
                        )
                        tool_results.append({
                            "tool_name": "PredictionTool",
                            "status": "success",
                            "source": "real",
                            "output": pred_result
                        })
                    except Exception as e:
                        logger.warning(f"Prediction tool failed: {e}")

            elif analysis_type == "ranking_reason":
                # 排名原因：战绩 + 排名 + 联赛整体情况
                team = entities.get('team') or entities.get('team_a')
                if team:
                    stats_result = await stats_tool.get_team_stats(team, last_n=10)
                    standing_result = await standings_tool.get_team_standing(team)

                    tool_results.append({
                        "tool_name": "StatsAnalysisTool",
                        "status": "success",
                        "source": "real",
                        "output": stats_result
                    })
                    tool_results.append({
                        "tool_name": "StandingsTool",
                        "status": "success",
                        "source": "real",
                        "output": standing_result
                    })

        except Exception as e:
            logger.error(f"[MatchAnalysisModule] Data collection failed: {e}", exc_info=True)

        return tool_results

    async def _perform_reasoning(
        self,
        query: str,
        structured_data: Dict,
        analysis_type: str
    ) -> Optional[Any]:
        """
        执行深度推理（使用ReasoningEngine）

        只在对比和预测场景下使用
        """
        if len(structured_data) < 2:
            logger.warning("[MatchAnalysisModule] Not enough data for reasoning")
            return None

        try:
            teams = list(structured_data.keys())
            team_a_data = structured_data[teams[0]]
            team_b_data = structured_data[teams[1]]

            # 多维度对比
            comparisons = self.data_analyzer.multi_dimensional_comparison(
                team_a_data,
                team_b_data
            )

            # 准备推理数据
            reasoning_data = self.data_analyzer.prepare_for_reasoning(
                structured_data,
                comparisons
            )

            # 调用推理引擎
            reasoning_result = await self.reasoning_engine.analyze_match_prediction(
                query=query,
                structured_data=reasoning_data,
                comparisons=comparisons
            )

            return reasoning_result

        except Exception as e:
            logger.error(f"[MatchAnalysisModule] Reasoning failed: {e}", exc_info=True)
            return None

    async def _generate_analysis(
        self,
        query: str,
        structured_data: Dict,
        reasoning: Optional[Any],
        analysis_type: str
    ) -> str:
        """
        用LLM生成深度分析文本
        """
        system_prompt = self._get_system_prompt(analysis_type)
        user_prompt = self._build_user_prompt(
            query,
            structured_data,
            reasoning,
            analysis_type
        )

        try:
            analysis = await llm_client.generate(system_prompt, user_prompt)
            return analysis

        except Exception as e:
            logger.error(f"[MatchAnalysisModule] LLM generation failed: {e}")
            # 降级：返回简单的数据摘要
            return self._fallback_analysis(structured_data, reasoning)

    def _get_system_prompt(self, analysis_type: str) -> str:
        """根据分析类型获取system prompt"""

        base_prompt = """你是一个资深的足球数据分析师。

分析要求：
1. **多维度**：从排名、状态、进攻、防守等多个角度分析
2. **有逻辑**：数据 → 分析 → 结论，清晰的推理链
3. **量化表达**：用具体数字和百分比，不要模糊表达
4. **关键洞察**：找出最核心的1-2个问题或优势

输出格式：
- 使用emoji增强可读性
- 分层展示（核心结论 → 数据支撑 → 详细分析）
- 简洁有力，避免废话
"""

        type_specific = {
            "team_status": """
特定任务：分析球队当前状态

输出结构：
1. 核心结论（一句话概括状态）
2. 数据支撑（3-5个关键数据点）
3. 核心问题或优势（1-2个）
4. 简要建议（可选）
""",
            "comparison": """
特定任务：对比两支球队

输出结构：
1. 核心结论（谁更强，优势多大）
2. 多维度对比（排名、状态、进攻、防守）
3. 各自优劣势
4. 综合评价
""",
            "prediction": """
特定任务：预测比赛结果

输出结构：
1. 核心预测（谁会赢，概率多少）
2. 数据支撑（为什么这么预测）
3. 风险因素（可能改变结果的因素）
4. 建议（可选）
""",
            "ranking_reason": """
特定任务：解释排名原因

输出结构：
1. 核心原因（最主要的1-2个因素）
2. 数据证据（用数据说明）
3. 趋势预测（排名会上升还是下降）
"""
        }

        return base_prompt + type_specific.get(analysis_type, "")

    def _build_user_prompt(
        self,
        query: str,
        structured_data: Dict,
        reasoning: Optional[Any],
        analysis_type: str
    ) -> str:
        """构建user prompt"""

        prompt = f"用户问：{query}\n\n"

        # 添加结构化数据
        prompt += "可用数据：\n"
        for team_name, team_data in structured_data.items():
            prompt += f"\n【{team_name}】\n"

            rank_text = str(team_data.rank) if team_data.rank else '未知'
            prompt += f"- 排名：{rank_text}\n"

            points_text = str(team_data.points) if team_data.points else '未知'
            prompt += f"- 积分：{points_text}\n"

            win_rate_text = f'{team_data.win_rate:.1%}' if team_data.win_rate is not None else '未知'
            prompt += f"- 胜率：{win_rate_text}\n"

            recent_win_rate_text = f'{team_data.recent_win_rate:.1%}' if team_data.recent_win_rate is not None else '未知'
            prompt += f"- 近期胜率：{recent_win_rate_text}\n"

        # 添加推理结果（如果有）
        if reasoning:
            prompt += f"\n推理分析：\n"
            prompt += f"- 结论：{reasoning.conclusion}\n"
            prompt += f"- 置信度：{reasoning.overall_confidence:.1%}\n"
            prompt += f"- 因果链：\n"
            for chain in reasoning.causal_chain[:3]:  # 只取前3个
                prompt += f"  * {chain}\n"

        prompt += "\n请进行深度分析。"

        return prompt

    def _fallback_analysis(
        self,
        structured_data: Dict,
        reasoning: Optional[Any]
    ) -> str:
        """降级分析（LLM不可用时）"""
        output = "📊 数据分析\n\n"

        for team_name, team_data in structured_data.items():
            output += f"【{team_name}】\n"
            output += f"- 排名：第{team_data.rank}位\n" if team_data.rank else ""
            output += f"- 积分：{team_data.points}分\n" if team_data.points else ""
            output += f"- 胜率：{team_data.win_rate:.1%}\n" if team_data.win_rate else ""
            output += "\n"

        if reasoning:
            output += f"\n💡 推理结论\n"
            output += f"{reasoning.conclusion}\n"
            output += f"置信度：{reasoning.overall_confidence:.1%}\n"

        return output
