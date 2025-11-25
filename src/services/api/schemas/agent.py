"""Agent 交互 API 的 Schema 定义。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union  # 👈 确保引入 Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentQuery(BaseModel):
    """Agent 对话入口的请求体。"""

    model_config = ConfigDict(strict=True)

    user_id: Optional[str] = None
    query: str
    # ✅ 修复：将 str | None 改为 Optional[str]
    preferred_phase: Optional[str] = Field(default="T-24h") 
    strategy_preference: Literal["balanced", "conservative", "aggressive"] = "balanced"


class ToolInvocation(BaseModel):
    """Planner 生成的步骤，供前端 Trace。"""

    model_config = ConfigDict(strict=True)

    tool_name: str
    input_payload: Dict[str, Any]
    output_snippet: str
    latency_ms: int


class AgentResponse(BaseModel):
    """Agent 响应，包含 Planner 生成的工具链。"""

    model_config = ConfigDict(strict=True)

    answer: str
    reasoning: str
    plan_steps: List[str] = Field(default_factory=list)
    tool_traces: List[ToolInvocation] = Field(default_factory=list)
    planner_version: str
    generated_at: datetime