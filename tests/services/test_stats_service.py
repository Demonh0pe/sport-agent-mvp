"""
StatsService 单元测试

测试覆盖：
1. 球队近况统计 (form)
2. 主客场统计
3. 历史交锋统计 (H2H)
4. 赛程密度计算
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime

pytestmark = pytest.mark.asyncio


class TestStatsServiceTeamForm:
    """测试 get_team_form 方法"""
    
    async def test_calculate_team_form(self):
        """测试计算球队近况"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            # 模拟球队
            mock_team = MagicMock()
            mock_team.team_id = "t1"
            mock_team.team_name = "Arsenal FC"
            
            # 模拟比赛数据：3胜1平1负
            mock_matches = []
            scores = [(2, 0), (1, 1), (3, 1), (0, 2), (2, 1)]  # (home, away)
            for i, (home_score, away_score) in enumerate(scores):
                match = MagicMock()
                match.home_team_id = "t1" if i % 2 == 0 else "t2"
                match.away_team_id = "t2" if i % 2 == 0 else "t1"
                match.home_score = home_score
                match.away_score = away_score
                match.status = "FINISHED"
                mock_matches.append(match)
            
            mock_data_service.get_recent_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(return_value=mock_team)
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_team_form("Arsenal", last_n=5)
            
            assert result is not None
            assert result.team_name == "Arsenal FC"
            assert result.matches_analyzed == 5
            # 验证胜平负场次计算
            assert result.wins + result.draws + result.losses == 5
    
    async def test_team_form_not_found(self):
        """测试球队未找到时返回 None"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            mock_data_service.get_recent_matches = AsyncMock(return_value=[])
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_team_form("不存在的球队", last_n=5)
            
            assert result is None


class TestStatsServiceHomeAwayStats:
    """测试 get_home_away_stats 方法"""
    
    async def test_home_stats(self):
        """测试主场统计"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            # 模拟球队
            mock_team = MagicMock()
            mock_team.team_id = "t1"
            mock_team.team_name = "Liverpool FC"
            
            # 模拟主场比赛：3胜1平1负
            mock_matches = []
            home_scores = [(2, 0), (1, 1), (3, 0), (0, 1), (2, 1)]
            for home_score, away_score in home_scores:
                match = MagicMock()
                match.home_team_id = "t1"  # 全部是主场
                match.away_team_id = "t2"
                match.home_score = home_score
                match.away_score = away_score
                mock_matches.append(match)
            
            mock_data_service.get_recent_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(return_value=mock_team)
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_home_away_stats("Liverpool", venue="home", last_n=5)
            
            assert result is not None
            assert result.venue == "home"
            # 比分分析: 2-0(胜), 1-1(平), 3-0(胜), 0-1(负), 2-1(胜) = 3胜1平1负
            assert result.wins == 3
            assert result.goals_for == 8  # 2+1+3+0+2
    
    async def test_away_stats(self):
        """测试客场统计"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            mock_team = MagicMock()
            mock_team.team_id = "t1"
            mock_team.team_name = "Chelsea FC"
            
            # 模拟客场比赛
            mock_matches = []
            for i in range(5):
                match = MagicMock()
                match.home_team_id = "t2"  # 对手主场
                match.away_team_id = "t1"  # 我们是客队
                match.home_score = 1
                match.away_score = 2
                mock_matches.append(match)
            
            mock_data_service.get_recent_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(return_value=mock_team)
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_home_away_stats("Chelsea", venue="away", last_n=5)
            
            assert result is not None
            assert result.venue == "away"
            assert result.wins == 5  # 全胜


class TestStatsServiceHeadToHead:
    """测试 get_head_to_head 方法"""
    
    async def test_h2h_stats(self):
        """测试历史交锋统计"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            # 模拟两支球队
            mock_team_a = MagicMock(team_id="t1", team_name="Man United")
            mock_team_b = MagicMock(team_id="t2", team_name="Man City")
            
            # 模拟历史交锋：A队3胜1平1负
            mock_matches = []
            results = [
                ("t1", "t2", 2, 1),  # A胜
                ("t2", "t1", 1, 2),  # A胜
                ("t1", "t2", 1, 1),  # 平
                ("t2", "t1", 2, 1),  # B胜
                ("t1", "t2", 3, 0),  # A胜
            ]
            for home_id, away_id, home_score, away_score in results:
                match = MagicMock()
                match.home_team_id = home_id
                match.away_team_id = away_id
                match.home_score = home_score
                match.away_score = away_score
                mock_matches.append(match)
            
            mock_data_service.get_head_to_head = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(side_effect=[mock_team_a, mock_team_b])
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_head_to_head("Man United", "Man City", last_n=5)
            
            assert result is not None
            assert result.total_matches == 5
            assert result.team_a_wins == 3
            assert result.team_b_wins == 1
            assert result.draws == 1


class TestStatsServiceScheduleDensity:
    """测试 get_schedule_density 方法"""
    
    async def test_congested_schedule(self):
        """测试密集赛程检测"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            mock_team = MagicMock(team_id="t1", team_name="Tottenham")
            
            # 模拟密集赛程：14天内6场比赛
            mock_matches = []
            for i in range(6):
                match = MagicMock()
                match.match_date = datetime(2024, 1, 1 + i * 2)  # 每2天一场
                mock_matches.append(match)
            
            mock_data_service.get_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(return_value=mock_team)
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_schedule_density(
                "Tottenham", 
                window_days=14,
                reference_date=date(2024, 1, 15)
            )
            
            assert result is not None
            assert result.matches_in_window == 6
            assert result.is_congested is True  # 平均2天一场，很密集
    
    async def test_relaxed_schedule(self):
        """测试宽松赛程"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            mock_team = MagicMock(team_id="t1", team_name="Newcastle")
            
            # 模拟宽松赛程：14天内2场比赛
            mock_matches = [
                MagicMock(match_date=datetime(2024, 1, 1)),
                MagicMock(match_date=datetime(2024, 1, 14)),
            ]
            
            mock_data_service.get_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(return_value=mock_team)
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.get_schedule_density(
                "Newcastle",
                window_days=14,
                reference_date=date(2024, 1, 15)
            )
            
            assert result is not None
            assert result.matches_in_window == 2
            assert result.avg_rest_days == 13.0
            assert result.is_congested is False


class TestStatsServiceComputeMatchFeatures:
    """测试 compute_match_features 方法"""
    
    async def test_compute_all_features(self):
        """测试计算完整比赛特征"""
        with patch("src.services.stats_service.data_service") as mock_data_service:
            # 模拟球队
            mock_home_team = MagicMock(team_id="t1", team_name="Arsenal")
            mock_away_team = MagicMock(team_id="t2", team_name="Chelsea")
            
            # 模拟比赛数据
            mock_matches = [MagicMock(
                home_team_id="t1",
                away_team_id="t2",
                home_score=2,
                away_score=1,
                status="FINISHED",
                match_date=datetime.now()
            )]
            
            # 模拟积分榜
            mock_standing = MagicMock(position=3, points=50)
            
            mock_data_service.get_recent_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team = AsyncMock(side_effect=[
                mock_home_team, mock_home_team, mock_away_team, mock_away_team,
                mock_home_team, mock_away_team,  # for H2H
                mock_home_team, mock_away_team   # for density
            ])
            mock_data_service.get_head_to_head = AsyncMock(return_value=mock_matches)
            mock_data_service.get_matches = AsyncMock(return_value=mock_matches)
            mock_data_service.get_team_standing = AsyncMock(return_value=mock_standing)
            
            from src.services.stats_service import StatsService
            service = StatsService()
            
            result = await service.compute_match_features("Arsenal", "Chelsea")
            
            assert result is not None
            assert "home_team" in result
            assert "away_team" in result
            assert "head_to_head" in result
            assert "computed_at" in result

