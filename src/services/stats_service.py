"""
StatsService - 统计特征服务层

职责：
1. 基于 DataService 提供的数据计算统计特征
2. 不直接访问数据库或外部 API
3. 提供球队状态、近况、主客场、H2H 等统计分析

注意：
- 纯 Python 实现，不依赖 LangChain
- 依赖 DataService 获取原始数据
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from collections import Counter

from src.services.data_service import data_service
from src.services.config import stats_config
from src.infra.db.models import Match

logger = logging.getLogger(__name__)


# ==================== 数据类定义 ====================

@dataclass
class TeamFormStats:
    """球队近况统计"""
    team_name: str
    matches_analyzed: int
    wins: int
    draws: int
    losses: int
    win_rate: float
    goals_for: int
    goals_against: int
    goal_difference: int
    avg_goals_for: float
    avg_goals_against: float
    form_string: str  # "W-W-D-L-W"
    points: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HomeAwayStats:
    """主客场统计"""
    team_name: str
    venue: str  # "home" or "away"
    matches_analyzed: int
    wins: int
    draws: int
    losses: int
    win_rate: float
    goals_for: int
    goals_against: int
    avg_goals_for: float
    avg_goals_against: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HeadToHeadStats:
    """历史交锋统计"""
    team_a_name: str
    team_b_name: str
    total_matches: int
    team_a_wins: int
    team_b_wins: int
    draws: int
    team_a_goals: int
    team_b_goals: int
    last_5_results: List[str]  # ["A_WIN", "DRAW", "B_WIN", ...]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScheduleDensity:
    """赛程密度统计（疲劳度）"""
    team_name: str
    matches_in_window: int
    window_days: int
    avg_rest_days: float
    is_congested: bool  # 是否赛程密集
    
    def to_dict(self) -> dict:
        return asdict(self)


# ==================== StatsService ====================

class StatsService:
    """
    统计特征服务
    
    提供各种球队统计指标的计算：
    - 近期状态 (form)
    - 主客场表现
    - 历史交锋 (H2H)
    - 赛程密度
    """
    
    def __init__(self):
        self._data_service = data_service
        self._config = stats_config
    
    # ==================== 近期状态 ====================
    
    async def get_team_form(
        self,
        team_name: str,
        last_n: int = 5,
        before_date: Optional[date] = None
    ) -> Optional[TeamFormStats]:
        """
        计算球队近期状态
        
        Args:
            team_name: 球队名称
            last_n: 最近场次数
            before_date: 截止日期
            
        Returns:
            球队近况统计
        """
        matches = await self._data_service.get_recent_matches(
            team_name=team_name,
            last_n=last_n,
            before_date=before_date
        )
        
        if not matches:
            logger.warning(f"No matches found for team: {team_name}")
            return None
        
        team = await self._data_service.get_team(team_name)
        if not team:
            return None
        
        # 统计指标
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        form_list = []
        
        for match in reversed(matches):  # 按时间正序
            is_home = match.home_team_id == team.team_id
            
            if is_home:
                gf = match.home_score or 0
                ga = match.away_score or 0
            else:
                gf = match.away_score or 0
                ga = match.home_score or 0
            
            goals_for += gf
            goals_against += ga
            
            # 判断胜负
            if gf > ga:
                wins += 1
                form_list.append("W")
            elif gf < ga:
                losses += 1
                form_list.append("L")
            else:
                draws += 1
                form_list.append("D")
        
        matches_count = len(matches)
        win_rate = wins / matches_count if matches_count > 0 else 0.0
        avg_gf = goals_for / matches_count if matches_count > 0 else 0.0
        avg_ga = goals_against / matches_count if matches_count > 0 else 0.0
        points = (wins * self._config.POINTS_PER_WIN + 
                 draws * self._config.POINTS_PER_DRAW)
        
        return TeamFormStats(
            team_name=team.team_name,
            matches_analyzed=matches_count,
            wins=wins,
            draws=draws,
            losses=losses,
            win_rate=round(win_rate, 3),
            goals_for=goals_for,
            goals_against=goals_against,
            goal_difference=goals_for - goals_against,
            avg_goals_for=round(avg_gf, 2),
            avg_goals_against=round(avg_ga, 2),
            form_string="-".join(form_list),
            points=points
        )
    
    # ==================== 主客场统计 ====================
    
    async def get_home_away_stats(
        self,
        team_name: str,
        venue: str = "home",
        last_n: int = 10
    ) -> Optional[HomeAwayStats]:
        """
        计算球队主场或客场表现
        
        Args:
            team_name: 球队名称
            venue: "home" 或 "away"
            last_n: 最近场次数
            
        Returns:
            主客场统计
        """
        all_matches = await self._data_service.get_recent_matches(
            team_name=team_name,
            last_n=last_n * 2  # 取两倍，因为要过滤主/客场
        )
        
        team = await self._data_service.get_team(team_name)
        if not team:
            return None
        
        # 过滤主场或客场比赛
        if venue == "home":
            matches = [m for m in all_matches if m.home_team_id == team.team_id]
        else:
            matches = [m for m in all_matches if m.away_team_id == team.team_id]
        
        matches = matches[:last_n]  # 取最近 N 场
        
        if not matches:
            return None
        
        # 统计
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        
        for match in matches:
            is_home = match.home_team_id == team.team_id
            
            if is_home:
                gf = match.home_score or 0
                ga = match.away_score or 0
            else:
                gf = match.away_score or 0
                ga = match.home_score or 0
            
            goals_for += gf
            goals_against += ga
            
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1
        
        matches_count = len(matches)
        win_rate = wins / matches_count if matches_count > 0 else 0.0
        avg_gf = goals_for / matches_count if matches_count > 0 else 0.0
        avg_ga = goals_against / matches_count if matches_count > 0 else 0.0
        
        return HomeAwayStats(
            team_name=team.team_name,
            venue=venue,
            matches_analyzed=matches_count,
            wins=wins,
            draws=draws,
            losses=losses,
            win_rate=round(win_rate, 3),
            goals_for=goals_for,
            goals_against=goals_against,
            avg_goals_for=round(avg_gf, 2),
            avg_goals_against=round(avg_ga, 2)
        )
    
    # ==================== 历史交锋 ====================
    
    async def get_head_to_head(
        self,
        team_a_name: str,
        team_b_name: str,
        last_n: int = 10
    ) -> Optional[HeadToHeadStats]:
        """
        计算两队历史交锋记录
        
        Args:
            team_a_name: 球队A名称
            team_b_name: 球队B名称
            last_n: 最近场次数
            
        Returns:
            历史交锋统计
        """
        matches = await self._data_service.get_head_to_head(
            team_a_name=team_a_name,
            team_b_name=team_b_name,
            last_n=last_n
        )
        
        if not matches:
            logger.warning(f"No H2H matches found: {team_a_name} vs {team_b_name}")
            return None
        
        team_a = await self._data_service.get_team(team_a_name)
        team_b = await self._data_service.get_team(team_b_name)
        
        if not team_a or not team_b:
            return None
        
        # 统计
        team_a_wins = 0
        team_b_wins = 0
        draws = 0
        team_a_goals = 0
        team_b_goals = 0
        last_5_results = []
        
        for i, match in enumerate(reversed(matches)):  # 按时间正序
            a_is_home = match.home_team_id == team_a.team_id
            
            if a_is_home:
                a_score = match.home_score or 0
                b_score = match.away_score or 0
            else:
                a_score = match.away_score or 0
                b_score = match.home_score or 0
            
            team_a_goals += a_score
            team_b_goals += b_score
            
            if a_score > b_score:
                team_a_wins += 1
                result = "A_WIN"
            elif a_score < b_score:
                team_b_wins += 1
                result = "B_WIN"
            else:
                draws += 1
                result = "DRAW"
            
            # 记录最近5场结果
            if i < 5:
                last_5_results.append(result)
        
        return HeadToHeadStats(
            team_a_name=team_a.team_name,
            team_b_name=team_b.team_name,
            total_matches=len(matches),
            team_a_wins=team_a_wins,
            team_b_wins=team_b_wins,
            draws=draws,
            team_a_goals=team_a_goals,
            team_b_goals=team_b_goals,
            last_5_results=last_5_results[:5]
        )
    
    # ==================== 赛程密度 ====================
    
    async def get_schedule_density(
        self,
        team_name: str,
        window_days: int = 14,
        reference_date: Optional[date] = None
    ) -> Optional[ScheduleDensity]:
        """
        计算球队赛程密度（疲劳度分析）
        
        Args:
            team_name: 球队名称
            window_days: 统计窗口天数
            reference_date: 参考日期（默认今天）
            
        Returns:
            赛程密度统计
        """
        if reference_date is None:
            reference_date = date.today()
        
        start_date = reference_date - timedelta(days=window_days)
        
        # 获取窗口内的比赛
        matches = await self._data_service.get_matches(
            team_name=team_name,
            date_from=start_date,
            date_to=reference_date,
            status="FINISHED"
        )
        
        if not matches or len(matches) < 2:
            return None
        
        team = await self._data_service.get_team(team_name)
        if not team:
            return None
        
        # 计算比赛间隔
        match_dates = sorted([m.match_date.date() for m in matches])
        rest_days = []
        
        for i in range(1, len(match_dates)):
            days_between = (match_dates[i] - match_dates[i-1]).days
            rest_days.append(days_between)
        
        avg_rest = sum(rest_days) / len(rest_days) if rest_days else 0
        
        # 判断是否赛程密集
        is_congested = (avg_rest < self._config.CONGESTION_THRESHOLD_DAYS and 
                       len(matches) >= self._config.MIN_MATCHES_FOR_CONGESTION)
        
        return ScheduleDensity(
            team_name=team.team_name,
            matches_in_window=len(matches),
            window_days=window_days,
            avg_rest_days=round(avg_rest, 1),
            is_congested=is_congested
        )
    
    # ==================== 综合特征 ====================
    
    async def compute_match_features(
        self,
        home_team_name: str,
        away_team_name: str,
        reference_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        计算比赛的所有统计特征（供预测使用）
        
        Args:
            home_team_name: 主队名称
            away_team_name: 客队名称
            reference_date: 参考日期
            
        Returns:
            特征字典
        """
        # 并发获取各项统计
        home_form = await self.get_team_form(home_team_name, last_n=5, before_date=reference_date)
        away_form = await self.get_team_form(away_team_name, last_n=5, before_date=reference_date)
        
        home_home_stats = await self.get_home_away_stats(home_team_name, venue="home", last_n=5)
        away_away_stats = await self.get_home_away_stats(away_team_name, venue="away", last_n=5)
        
        h2h = await self.get_head_to_head(home_team_name, away_team_name, last_n=5)
        
        home_density = await self.get_schedule_density(home_team_name, window_days=14, reference_date=reference_date)
        away_density = await self.get_schedule_density(away_team_name, window_days=14, reference_date=reference_date)
        
        # 获取积分榜位置
        home_standing = await self._data_service.get_team_standing(home_team_name)
        away_standing = await self._data_service.get_team_standing(away_team_name)
        
        return {
            "home_team": {
                "name": home_team_name,
                "form": home_form.to_dict() if home_form else None,
                "home_stats": home_home_stats.to_dict() if home_home_stats else None,
                "standing_position": home_standing.position if home_standing else None,
                "schedule_density": home_density.to_dict() if home_density else None
            },
            "away_team": {
                "name": away_team_name,
                "form": away_form.to_dict() if away_form else None,
                "away_stats": away_away_stats.to_dict() if away_away_stats else None,
                "standing_position": away_standing.position if away_standing else None,
                "schedule_density": away_density.to_dict() if away_density else None
            },
            "head_to_head": h2h.to_dict() if h2h else None,
            "computed_at": datetime.now().isoformat()
        }


# 全局单例
stats_service = StatsService()

