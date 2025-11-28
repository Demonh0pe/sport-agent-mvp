"""FastAPI 依赖注入：管理服务实例的生命周期。"""
from __future__ import annotations

from functools import lru_cache

from src.services.agent_service_v3 import AgentServiceV3, agent_service_v3
from src.shared.config import Settings, get_settings

# 1. 获取全局配置的依赖
def get_app_settings() -> Settings:
    return get_settings()

# 2. 获取 AgentServiceV3 的依赖 (使用全局单例)
def get_agent_service_v3() -> AgentServiceV3:
    """
    获取 v3.0 版本的 Agent 服务（Supervisor + Expert Agents 架构）
    
    使用全局单例以保持会话记忆和状态
    """
    return agent_service_v3