"""
AgentServiceV3 - 基于新架构的 Agent 服务

架构：Supervisor + Expert Agents 多智能体模式

核心组件：
1. SupervisorAgent - 监督智能体（任务规划、专家调度、结果合成）
2. ExpertRegistry - 专家注册表（管理所有 Expert Agents）
3. Expert Agents:
   - DataStatsAgent - 数据统计专家
   - PredictionAgent - 预测专家
   - KnowledgeAgent - 知识专家（待实现）

服务层（纯Python，不依赖LangChain）：
- DataService - 数据访问
- StatsService - 统计特征
- PredictService - 预测逻辑
- KnowledgeService - RAG 知识（待实现）

使用方式：
```python
from src.services.agent_service_v3 import agent_service_v3

response = await agent_service_v3.chat("曼联最近状态怎么样？")
print(response["answer"])
```
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.supervisor.supervisor_agent import SupervisorAgent
from src.supervisor.expert_registry import ExpertRegistry
from src.shared.llm_client_v2 import get_llm_client

logger = logging.getLogger(__name__)


class AgentServiceV3:
    """
    Agent 服务 V3.0
    
    基于 Supervisor + Expert Agents 的多智能体架构
    
    优势：
    - 清晰的分层架构
    - Service 层可独立测试和复用
    - Expert 可单独优化和扩展
    - 基于 LangChain 的标准实现
    """
    
    def __init__(self):
        """初始化 Agent Service V3"""
        logger.info("Initializing AgentServiceV3...")
        
        # 获取全局 LLM 客户端
        llm_client = get_llm_client()
        
        # 1. 初始化 Expert Registry
        self._expert_registry = ExpertRegistry(llm_client)
        
        # 2. 获取 Expert Tools
        expert_tools = self._expert_registry.as_tools()
        
        # 3. 初始化 Supervisor Agent
        self._supervisor = SupervisorAgent(
            expert_tools=expert_tools,
            llm_client_instance=llm_client,
            enable_memory=True
        )
        
        logger.info(f"AgentServiceV3 initialized with {len(expert_tools)} expert tools")
    
    async def chat(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户查询（主入口）
        
        Args:
            query: 用户自然语言查询
            session_id: 会话 ID（用于上下文管理）
            context: 额外上下文信息
            
        Returns:
            {
                "answer": str,              # 最终自然语言回答
                "tools_used": list,         # 使用的工具列表
                "session_id": str,
                "timestamp": str,
                "duration_seconds": float,
                "status": str               # "success" / "error"
            }
        """
        try:
            # 调用 Supervisor Agent
            result = await self._supervisor.run(
                query=query,
                session_id=session_id,
                context=context
            )
            
            return {
                "answer": result["answer"],
                "tools_used": result["tools_used"],
                "session_id": result["session_id"],
                "timestamp": result["timestamp"],
                "duration_seconds": result.get("duration_seconds", 0),
                "status": "success" if "error" not in result else "error"
            }
            
        except Exception as e:
            logger.error(f"AgentServiceV3.chat failed: {e}", exc_info=True)
            return {
                "answer": f"处理您的问题时遇到错误：{str(e)}",
                "tools_used": [],
                "session_id": session_id or "default",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 0,
                "status": "error",
                "error": str(e)
            }
    
    def list_available_experts(self) -> list:
        """
        列出所有可用的专家
        
        Returns:
            专家名称列表
        """
        return self._expert_registry.list_experts()
    
    async def direct_call_expert(
        self,
        expert_name: str,
        query: str
    ) -> Dict[str, Any]:
        """
        直接调用指定的专家（绕过 Supervisor）
        
        用于测试或特定场景
        
        Args:
            expert_name: 专家名称 ("data_stats" / "prediction" / "knowledge")
            query: 查询
            
        Returns:
            专家响应
        """
        expert = self._expert_registry.get_expert(expert_name)
        if not expert:
            return {
                "output": f"专家 {expert_name} 不存在",
                "status": "error"
            }
        
        try:
            result = await expert.arun(query)
            return result
        except Exception as e:
            logger.error(f"Direct call to {expert_name} failed: {e}")
            return {
                "output": f"调用专家失败：{str(e)}",
                "status": "error"
            }


# 全局单例
agent_service_v3 = AgentServiceV3()


# ==================== 便捷接口 ====================

async def ask(query: str, session_id: Optional[str] = None) -> str:
    """
    便捷问答接口（只返回答案文本）
    
    Args:
        query: 用户问题
        session_id: 会话 ID
        
    Returns:
        答案文本
    """
    result = await agent_service_v3.chat(query, session_id)
    return result["answer"]


async def ask_expert(expert: str, query: str) -> str:
    """
    直接向指定专家提问
    
    Args:
        expert: 专家名称 ("data_stats" / "prediction")
        query: 问题
        
    Returns:
        答案文本
    """
    result = await agent_service_v3.direct_call_expert(expert, query)
    return result.get("output", "")

