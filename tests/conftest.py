"""
Pytest 配置文件

提供测试固件和通用配置：
1. 异步测试支持
2. 数据库会话 Mock
3. HTTP 客户端固件
4. 工具执行器固件
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# 设置测试环境
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("USE_MOCK_TOOLS", "true")


# ============ 异步事件循环 ============

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建会话级别的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============ 数据库相关 ============

@pytest_asyncio.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    """
    Mock 数据库会话
    
    用于单元测试，不连接真实数据库
    """
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    yield session


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    """
    真实数据库会话（用于集成测试）
    
    注意：需要配置测试数据库
    """
    try:
        from src.infra.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            yield session
            await session.rollback()  # 测试后回滚
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ============ HTTP 客户端 ============

@pytest_asyncio.fixture
async def client() -> AsyncGenerator:
    """
    FastAPI 测试客户端
    
    使用 httpx.AsyncClient 进行 API 测试
    """
    try:
        from httpx import AsyncClient, ASGITransport
        from src.services.api.main import app
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    except ImportError:
        pytest.skip("httpx not installed")


# ============ Agent Service V3 ============

@pytest.fixture
def mock_agent_service_v3() -> MagicMock:
    """
    Mock Agent Service V3
    
    用于测试 API 层，不执行真实 Agent
    """
    service = MagicMock()
    
    async def mock_chat(query, session_id=None, context=None):
        return {
            "answer": f"这是对「{query}」的 Mock 回答。",
            "tools_used": ["data_stats", "prediction"],
            "session_id": session_id or "test-session",
            "timestamp": "2025-11-27T12:00:00",
            "duration_seconds": 1.5,
            "status": "success"
        }
    
    service.chat = AsyncMock(side_effect=mock_chat)
    service.list_available_experts.return_value = ["data_stats", "prediction", "knowledge"]
    
    return service


# ============ LLM Client ============

@pytest.fixture
def mock_llm_client() -> MagicMock:
    """
    Mock LLM 客户端
    
    避免测试时调用真实 LLM API
    """
    client = MagicMock()
    client.generate = AsyncMock(return_value="这是一个 Mock 回答。")
    client.chat = AsyncMock(return_value="这是一个 Mock 聊天回答。")
    
    return client


# ============ 测试数据 ============

@pytest.fixture
def sample_team_data() -> dict:
    """示例球队数据"""
    return {
        "id": 1,
        "name": "Manchester United FC",
        "short_name": "Man United",
        "tla": "MUN",
        "country": "England",
    }


@pytest.fixture
def sample_match_data() -> dict:
    """示例比赛数据"""
    return {
        "id": 1,
        "home_team_id": 1,
        "away_team_id": 2,
        "home_score": 2,
        "away_score": 1,
        "status": "FINISHED",
        "matchday": 10,
    }


@pytest.fixture
def sample_standings_data() -> list:
    """示例积分榜数据"""
    return [
        {"position": 1, "team_id": 1, "team_name": "Team A", "points": 30, "played": 12},
        {"position": 2, "team_id": 2, "team_name": "Team B", "points": 28, "played": 12},
        {"position": 3, "team_id": 3, "team_name": "Team C", "points": 25, "played": 12},
    ]


# ============ 测试配置 ============

@pytest.fixture
def test_settings() -> MagicMock:
    """Mock 配置对象"""
    settings = MagicMock()
    settings.app_name = "Sport Agent Test"
    settings.app_version = "0.0.1-test"
    settings.service.agent.enable_trace = True
    settings.service.api.host = "localhost"
    settings.service.api.port = 8000
    
    return settings


# ============ 清理操作 ============

@pytest.fixture(autouse=True)
def cleanup():
    """每个测试后的清理操作"""
    yield
    # 测试完成后的清理逻辑
    pass

