"""
DataService 单元测试

测试覆盖：
1. 球队查询（包含别名解析）
2. 比赛查询
3. 积分榜查询
4. 历史交锋查询
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from contextlib import asynccontextmanager

pytestmark = pytest.mark.asyncio


class MockAsyncContextManager:
    """可重复使用的 Mock 异步上下文管理器"""
    
    def __init__(self, mock_session):
        self.mock_session = mock_session
    
    async def __aenter__(self):
        return self.mock_session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def create_mock_session():
    """创建正确配置的 Mock 数据库会话"""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session


class TestDataServiceGetTeam:
    """测试 get_team 方法"""
    
    async def test_get_team_by_exact_name(self):
        """测试精确名称匹配"""
        mock_session = create_mock_session()
        
        # 模拟查询结果
        mock_team = MagicMock()
        mock_team.team_id = "t1"
        mock_team.team_name = "Manchester United FC"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_result
        
        with patch("src.services.data_service.get_async_session") as mock_get_session:
            mock_get_session.return_value = MockAsyncContextManager(mock_session)
            
            from src.services.data_service import DataService
            service = DataService()
            service._resolver_initialized = True
            
            result = await service.get_team("t1")
            
            assert result is not None
            assert result.team_name == "Manchester United FC"
    
    async def test_get_team_not_found(self):
        """测试球队未找到的情况"""
        mock_session = create_mock_session()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with patch("src.services.data_service.get_async_session") as mock_get_session:
            mock_get_session.return_value = MockAsyncContextManager(mock_session)
            
            from src.services.data_service import DataService
            service = DataService()
            service._resolver_initialized = True
            
            # Mock entity resolver
            service._entity_resolver = MagicMock()
            service._entity_resolver.resolve_team = AsyncMock(return_value=None)
            
            result = await service.get_team("不存在的球队")
            
            assert result is None


class TestDataServiceGetMatches:
    """测试 get_matches 方法"""
    
    async def test_get_matches_with_limit(self):
        """测试带限制的比赛查询"""
        mock_session = create_mock_session()
        
        # 模拟比赛列表
        mock_matches = [
            MagicMock(match_id=f"m{i}", status="FINISHED")
            for i in range(5)
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_matches
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        with patch("src.services.data_service.get_async_session") as mock_get_session:
            mock_get_session.return_value = MockAsyncContextManager(mock_session)
            
            from src.services.data_service import DataService
            service = DataService()
            service._resolver_initialized = True
            
            result = await service.get_matches(limit=5)
            
            assert len(result) == 5


class TestDataServiceGetRecentMatches:
    """测试 get_recent_matches 方法"""
    
    async def test_get_recent_matches_for_team(self):
        """测试获取球队最近比赛"""
        mock_session = create_mock_session()
        
        # 模拟球队
        mock_team = MagicMock()
        mock_team.team_id = "t1"
        mock_team.team_name = "Arsenal FC"
        
        # 模拟比赛
        mock_matches = [
            MagicMock(
                match_id=f"m{i}",
                home_team_id="t1" if i % 2 == 0 else "t2",
                away_team_id="t2" if i % 2 == 0 else "t1",
                home_score=2,
                away_score=1,
                status="FINISHED"
            )
            for i in range(5)
        ]
        
        # 配置 side_effect 来处理多次调用
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_team
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = mock_matches
                result.scalars.return_value = mock_scalars
            call_count[0] += 1
            return result
        
        mock_session.execute.side_effect = execute_side_effect
        
        with patch("src.services.data_service.get_async_session") as mock_get_session:
            # 让每次调用都返回新的上下文管理器
            mock_get_session.return_value = MockAsyncContextManager(mock_session)
            
            from src.services.data_service import DataService
            service = DataService()
            service._resolver_initialized = True
            
            result = await service.get_recent_matches("Arsenal", last_n=5)
            
            assert len(result) == 5


class TestDataServiceGetStandings:
    """测试 get_standings 方法"""
    
    async def test_get_league_standings(self):
        """测试获取联赛积分榜"""
        mock_session = create_mock_session()
        
        # 模拟联赛
        mock_league = MagicMock()
        mock_league.league_id = "PL"
        mock_league.league_name = "Premier League"
        
        # 模拟积分榜
        mock_standings = [
            MagicMock(position=i+1, team_id=f"t{i}", points=90-i*3)
            for i in range(5)
        ]
        
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_league
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = mock_standings
                result.scalars.return_value = mock_scalars
            call_count[0] += 1
            return result
        
        mock_session.execute.side_effect = execute_side_effect
        
        with patch("src.services.data_service.get_async_session") as mock_get_session:
            mock_get_session.return_value = MockAsyncContextManager(mock_session)
            
            from src.services.data_service import DataService
            service = DataService()
            service._resolver_initialized = True
            
            result = await service.get_standings("Premier League")
            
            assert len(result) == 5
            assert result[0].position == 1


class TestDataServiceGetHeadToHead:
    """测试 get_head_to_head 方法"""
    
    async def test_get_h2h_records(self):
        """测试获取历史交锋记录"""
        mock_session = create_mock_session()
        
        # 模拟球队
        mock_team_a = MagicMock(team_id="t1", team_name="Team A")
        mock_team_b = MagicMock(team_id="t2", team_name="Team B")
        
        # 模拟历史交锋
        mock_matches = [
            MagicMock(
                match_id=f"m{i}",
                home_team_id="t1" if i % 2 == 0 else "t2",
                away_team_id="t2" if i % 2 == 0 else "t1",
                home_score=2,
                away_score=1,
                status="FINISHED"
            )
            for i in range(5)
        ]
        
        call_count = [0]
        
        def execute_side_effect(*args, **kwargs):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_team_a
            elif call_count[0] == 1:
                result.scalar_one_or_none.return_value = mock_team_b
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = mock_matches
                result.scalars.return_value = mock_scalars
            call_count[0] += 1
            return result
        
        mock_session.execute.side_effect = execute_side_effect
        
        with patch("src.services.data_service.get_async_session") as mock_get_session:
            mock_get_session.return_value = MockAsyncContextManager(mock_session)
            
            from src.services.data_service import DataService
            service = DataService()
            service._resolver_initialized = True
            
            result = await service.get_head_to_head("Team A", "Team B", last_n=5)
            
            assert len(result) == 5
