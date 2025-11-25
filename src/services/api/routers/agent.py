"""Agent 交互 API 的路由定义。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

# 引入 Schema
from src.services.api.schemas.agent import AgentQuery, AgentResponse
# 引入 依赖注入
from src.services.api.dependencies import get_agent_service, get_agent_service_v2
# 引入 Service 类型提示
from src.services.api.services.agent import AgentService
from src.services.api.services.agent_v2 import AgentServiceV2

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])

@router.post("/query", response_model=AgentResponse)
async def agent_query(
    payload: AgentQuery,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """
    Agent 查询接口 (v1.0 版本 - 兼容旧版)
    
    接收用户查询 -> 通过 Service 调用 Planner -> 返回结果
    """
    try:
        return await service.run_query(payload)
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Agent Service Error")


@router.post("/query/v2", response_model=AgentResponse)
async def agent_query_v2(
    payload: AgentQuery,
    service: AgentServiceV2 = Depends(get_agent_service_v2),
) -> AgentResponse:
    """
    Agent 查询接口 (v2.0 版本 - 统一架构)
    
    新特性：
    - ✅ 统一使用 Orchestrator 架构
    - ✅ 智能工具路由（真实工具 + Mock 工具）
    - ✅ 改进的参数解析和绑定
    - ✅ 更详细的执行追踪
    - ✅ 更好的错误处理
    
    使用示例：
    ```
    POST /api/v1/agent/query/v2
    {
      "query": "曼联最近的比赛情况如何？"
    }
    ```
    """
    try:
        return await service.run_query(payload)
    except Exception as e:
        print(f"Error in v2: {e}")
        raise HTTPException(status_code=500, detail="Agent Service V2 Error")