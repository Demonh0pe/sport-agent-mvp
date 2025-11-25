"""FastAPI 依赖注入：管理服务实例的生命周期。"""
from __future__ import annotations

from functools import lru_cache

from src.services.api.services.agent import AgentService
from src.services.api.services.agent_v2 import AgentServiceV2
from src.shared.config import Settings, get_settings

# 1. 获取全局配置的依赖
def get_app_settings() -> Settings:
    return get_settings()

# 2. 获取 AgentService 的依赖 (单例模式) - 旧版本
@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    # 依赖注入链：Settings -> AgentService
    settings = get_settings()
    return AgentService(settings=settings)

# 3. 获取 AgentServiceV2 的依赖 (单例模式) - 新版本
@lru_cache(maxsize=1)
def get_agent_service_v2() -> AgentServiceV2:
    """获取 v2.0 版本的 Agent 服务（统一架构）"""
    settings = get_settings()
    return AgentServiceV2(settings=settings)