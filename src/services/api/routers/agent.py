"""Agent 交互 API 的路由定义。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# 引入 Schema
from src.services.api.schemas.agent import AgentQuery
# 引入 依赖注入
from src.services.api.dependencies import get_agent_service_v3
# 引入 Service
from src.services.agent_service_v3 import AgentServiceV3

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


class AgentResponseV3(BaseModel):
    """V3 Agent 响应模型"""
    answer: str
    tools_used: list[str]
    session_id: str
    timestamp: str
    duration_seconds: float
    status: str


@router.post("/chat", response_model=AgentResponseV3)
async def agent_chat(
    payload: AgentQuery,
    session_id: Optional[str] = Query(None, description="会话ID，用于保持对话上下文"),
    service: AgentServiceV3 = Depends(get_agent_service_v3),
) -> AgentResponseV3:
    """
    Agent 对话接口 (v3.0 版本 - Supervisor + Expert Agents 架构)
    
    **架构特点：**
    - [OK] SupervisorAgent 负责任务规划和专家调度
    - [OK] 多个 Expert Agents（DataStatsAgent、PredictionAgent）
    - [OK] 基于 LangChain 的标准实现
    - [OK] 支持会话记忆，可进行多轮对话
    - [OK] Service 层无 LangChain 依赖，可独立测试
    
    **使用示例：**
    ```bash
    # 单轮查询
    POST /api/v1/agent/chat
    {
      "query": "曼联最近的比赛情况如何？"
    }
    
    # 多轮对话（使用 session_id）
    POST /api/v1/agent/chat?session_id=user123
    {
      "query": "那利物浦呢？"
    }
    ```
    
    **返回字段：**
    - answer: 最终自然语言回答
    - tools_used: 使用的工具/专家列表
    - session_id: 会话ID
    - timestamp: 时间戳
    - duration_seconds: 耗时
    - status: 状态（success/error）
    """
    try:
        logger.info(f"Processing query: {payload.query}")
        
        result = await service.chat(
            query=payload.query,
            session_id=session_id,
            context=None
        )
        
        return AgentResponseV3(**result)
        
    except Exception as e:
        logger.error(f"Agent chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent 服务错误: {str(e)}"
        )


@router.get("/experts", response_model=dict)
async def list_experts(
    service: AgentServiceV3 = Depends(get_agent_service_v3),
) -> dict:
    """
    列出所有可用的专家智能体
    
    **返回示例：**
    ```json
    {
      "experts": [
        "data_stats",
        "prediction",
        "knowledge"
      ],
      "total": 3
    }
    ```
    """
    experts = service.list_available_experts()
    return {
        "experts": experts,
        "total": len(experts)
    }