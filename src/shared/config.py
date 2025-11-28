"""全局配置加载与强类型定义。
该模块负责读取 config/ 目录下的 YAML 文件，并映射为 Pydantic 模型。
"""
from __future__ import annotations

import functools
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 定位到项目根目录
BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"

def _load_yaml(filename: str) -> Dict[str, Any]:
    """辅助函数：安全加载 YAML 文件"""
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# --- 1. DB Config Model ---
class DbConnection(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    schema_name: str = Field(alias="schema", default="public")

class DbConfig(BaseModel):
    default: DbConnection
    analytics: Optional[DbConnection] = None

# --- 2. Service Config Model ---
class ApiConfig(BaseModel):
    host: str
    port: int
    log_level: str
    enable_docs: bool

class PredictionServiceConfig(BaseModel):
    cache_ttl_seconds: int
    default_phase: str
    cold_start_threshold: int

class NewsServiceConfig(BaseModel):
    default_window_hours: int
    max_items: int

# [新增] LLM 配置模型
class LLMConfig(BaseModel):
    provider: str
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7

# [修改] 把 LLM 配置加入 AgentConfig
class AgentConfig(BaseModel):
    max_turns: int
    enable_trace: bool
    # 这里加了 Optional 是为了防止你 yaml 还没配好时报错，
    # 但既然你已经配了，它会自动读取
    llm: Optional[LLMConfig] = None 

class ServiceConfig(BaseModel):
    api: ApiConfig
    prediction_service: PredictionServiceConfig
    news_service: NewsServiceConfig
    agent: AgentConfig
    data_source: Optional[DataSourceConfig] = None

# --- 3. Feature Store Model ---
class RedisCacheConfig(BaseModel):
    backend: str
    url: str

class FeatureSet(BaseModel):
    storage: str
    path: str
    primary_keys: Optional[List[str]] = None
    ttl_hours: Optional[int] = None
    cache: Optional[RedisCacheConfig] = None

class FeatureStoreConfig(BaseModel):
    match_features: FeatureSet
    team_snapshot: FeatureSet
    player_snapshot: FeatureSet

# --- 4. Model Config ---
class CalibrationConfig(BaseModel):
    method: str
    last_updated: datetime

class XGBModelConfig(BaseModel):
    active_version: str
    registry_path: str
    fallback: str
    calibration: CalibrationConfig

class EloConfig(BaseModel):
    k_factor: int
    home_advantage: int

class ModelConfig(BaseModel):
    prediction: XGBModelConfig
    elo_diff_baseline: EloConfig

# --- 5. Agent Tools Model ---
class ToolDefinition(BaseModel):
    name: str
    description: str
    endpoint: str
    method: str
    params: List[str]

class AgentToolsConfig(BaseModel):
    tools: List[ToolDefinition]

# --- 6. Data Source Model ---
class FootballDataOrgConfig(BaseModel):
    base_url: str
    api_key: str
    enabled: bool

class DataSourceConfig(BaseModel):
    football_data_org: FootballDataOrgConfig

# --- 全局 Settings 聚合 ---
class Settings(BaseSettings):
    app_name: str = "Sport Agent MVP"
    app_version: str = "0.1.0"
    environment: str = "dev"
    
    db: DbConfig = Field(default_factory=lambda: DbConfig(**_load_yaml("db.yaml")))
    service: ServiceConfig = Field(default_factory=lambda: ServiceConfig(**_load_yaml("service.yaml")))
    feature_store: FeatureStoreConfig = Field(default_factory=lambda: FeatureStoreConfig(**_load_yaml("feature_store.yaml")))
    model: ModelConfig = Field(default_factory=lambda: ModelConfig(**_load_yaml("model.yaml")))
    agent_tools: AgentToolsConfig = Field(default_factory=lambda: AgentToolsConfig(**_load_yaml("agent_tools.yaml")))

    class Config:
        env_prefix = "SPORT_AGENT_"

@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局单例配置。"""
    return Settings()