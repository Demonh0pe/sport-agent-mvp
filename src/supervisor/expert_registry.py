"""
ExpertRegistry - 专家注册表

职责：
1. 注册和管理所有的 Expert Agents
2. 将 Expert Agents 封装为 LangChain Tools
3. 提供给 SupervisorAgent 使用

设计模式：Expert-as-Tool
每个 Expert Agent 被包装为一个 Tool，Supervisor 通过调用 Tool 来使用 Expert
"""
from __future__ import annotations

import logging
from typing import List, TYPE_CHECKING

from langchain.tools import Tool

if TYPE_CHECKING:
    from src.shared.llm_client_v2 import LLMClient

logger = logging.getLogger(__name__)


class ExpertRegistry:
    """
    专家注册表
    
    管理所有 Expert Agents 并将其转换为 Tools
    """
    
    def __init__(self, llm_client: 'LLMClient'):
        """
        初始化专家注册表
        
        Args:
            llm_client: LLM 客户端实例（供 Expert Agents 使用）
        """
        self._llm_client = llm_client
        self._experts = {}
        
        # 延迟导入以避免循环依赖
        self._initialize_experts()
    
    def _initialize_experts(self):
        """
        初始化所有 Expert Agents
        
        注意：这里会导入 Expert Agent 类
        """
        logger.info("Initializing Expert Agents...")
        
        try:
            # 导入 Expert Agents
            from src.agent.data_stats_agent import DataStatsAgent
            from src.agent.prediction_agent import PredictionAgent
            # KnowledgeAgent 暂时注释，等 RAG 系统就绪后再添加
            # from src.agent.knowledge_agent import KnowledgeAgent
            
            # 实例化 Experts
            self._experts["data_stats"] = DataStatsAgent(self._llm_client)
            self._experts["prediction"] = PredictionAgent(self._llm_client)
            # self._experts["knowledge"] = KnowledgeAgent(self._llm_client)
            
            logger.info(f"Successfully initialized {len(self._experts)} experts")
            
        except ImportError as e:
            logger.warning(f"Some expert agents not yet implemented: {e}")
            # 如果 Expert Agents 还未实现，使用占位符
            self._experts = {}
    
    def as_tools(self) -> List[Tool]:
        """
        将所有 Expert Agents 转换为 LangChain Tools
        
        Returns:
            Tool 列表，供 Supervisor 使用
        """
        tools = []
        
        # DataStatsAgent → Tool
        if "data_stats" in self._experts:
            tools.append(
                Tool(
                    name="data_stats_expert",
                    description=(
                        "查询比赛、联赛、球队状态与统计特征时使用。"
                        "适用场景："
                        "- 查询比赛时间、结果、赛程"
                        "- 查询球队战绩、积分榜、排名"
                        "- 查询球队近期状态、主客场表现"
                        "- 查询历史交锋记录"
                        "输入：自然语言查询，如 '曼联最近5场比赛战绩'"
                        "输出：结构化数据或自然语言描述"
                    ),
                    func=self._create_expert_caller("data_stats"),
                    coroutine=self._create_expert_caller_async("data_stats")
                )
            )
        
        # PredictionAgent → Tool
        if "prediction" in self._experts:
            tools.append(
                Tool(
                    name="prediction_expert",
                    description=(
                        "对给定比赛进行胜平负预测并输出结构化结果时使用。"
                        "适用场景："
                        "- 预测具体比赛的胜负"
                        "- 分析双方实力对比"
                        "- 给出概率和关键影响因素"
                        "输入：自然语言查询，如 '阿森纳对曼城谁会赢'"
                        "输出：预测概率、关键因素、数据依据"
                    ),
                    func=self._create_expert_caller("prediction"),
                    coroutine=self._create_expert_caller_async("prediction")
                )
            )
        
        # KnowledgeAgent → Tool (暂时注释)
        # if "knowledge" in self._experts:
        #     tools.append(
        #         Tool(
        #             name="knowledge_expert",
        #             description=(
        #                 "解释规则、战术、比赛关键点、战术名词时使用。"
        #                 "适用场景："
        #                 "- 解释足球规则（越位、犯规等）"
        #                 "- 解释战术体系（4-3-3、反击等）"
        #                 "- 回答足球知识类问题"
        #                 "输入：自然语言问题，如 '什么是越位'"
        #                 "输出：详细解释和说明"
        #             ),
        #             func=self._create_expert_caller("knowledge"),
        #             coroutine=self._create_expert_caller_async("knowledge")
        #         )
        #     )
        
        logger.info(f"Registered {len(tools)} expert tools")
        return tools
    
    def _create_expert_caller(self, expert_name: str):
        """
        创建同步的 Expert 调用函数
        
        Args:
            expert_name: 专家名称
            
        Returns:
            可调用的函数
        """
        def caller(query: str) -> str:
            """调用指定的 Expert Agent"""
            try:
                expert = self._experts.get(expert_name)
                if not expert:
                    return f"专家 {expert_name} 暂不可用"
                
                # 调用 Expert 的 run 方法
                result = expert.run(query)
                
                # 如果返回字典，提取 output
                if isinstance(result, dict):
                    return result.get("output", str(result))
                
                return str(result)
                
            except Exception as e:
                logger.error(f"Expert {expert_name} call failed: {e}")
                return f"调用专家 {expert_name} 时出错：{str(e)}"
        
        return caller
    
    def _create_expert_caller_async(self, expert_name: str):
        """
        创建异步的 Expert 调用函数
        
        Args:
            expert_name: 专家名称
            
        Returns:
            异步可调用的函数
        """
        async def caller_async(query: str) -> str:
            """异步调用指定的 Expert Agent"""
            try:
                expert = self._experts.get(expert_name)
                if not expert:
                    return f"专家 {expert_name} 暂不可用"
                
                # 调用 Expert 的异步 run 方法
                if hasattr(expert, "arun"):
                    result = await expert.arun(query)
                else:
                    # 如果没有异步方法，使用同步方法
                    result = expert.run(query)
                
                # 如果返回字典，提取 output
                if isinstance(result, dict):
                    return result.get("output", str(result))
                
                return str(result)
                
            except Exception as e:
                logger.error(f"Expert {expert_name} call failed: {e}")
                return f"调用专家 {expert_name} 时出错：{str(e)}"
        
        return caller_async
    
    def get_expert(self, expert_name: str):
        """
        获取指定的 Expert Agent 实例
        
        Args:
            expert_name: 专家名称
            
        Returns:
            Expert Agent 实例
        """
        return self._experts.get(expert_name)
    
    def list_experts(self) -> List[str]:
        """
        列出所有已注册的专家
        
        Returns:
            专家名称列表
        """
        return list(self._experts.keys())

