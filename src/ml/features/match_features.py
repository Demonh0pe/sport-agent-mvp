"""
比赛特征提取器

从历史比赛数据中提取特征用于预测
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import Match, Team, Standing
from src.infra.db.session import AsyncSessionLocal


class MatchFeatureExtractor:
    """比赛特征提取器"""
    
    def __init__(self):
        self.feature_names = [
            # 球队基础特征
            "home_team_rank",
            "away_team_rank",
            "rank_diff",
            
            # 积分榜特征
            "home_team_points",
            "away_team_points",
            "points_diff",
            
            # 进球能力
            "home_team_goals_for",
            "away_team_goals_for",
            "home_team_goals_against",
            "away_team_goals_against",
            
            # 近期状态（最近5场）
            "home_recent_wins",
            "home_recent_draws",
            "home_recent_losses",
            "away_recent_wins",
            "away_recent_draws",
            "away_recent_losses",
            
            # 主客场优势
            "home_advantage_win_rate",
            "away_disadvantage_win_rate",
            
            # 对阵历史
            "head_to_head_home_wins",
            "head_to_head_draws",
            "head_to_head_away_wins",
        ]
    
    async def extract_features_for_match(
        self, 
        home_team_id: str, 
        away_team_id: str,
        league_id: str,
        match_date: datetime,
        season: str = "2024"
    ) -> Dict[str, float]:
        """
        为单场比赛提取特征
        
        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            league_id: 联赛ID
            match_date: 比赛日期
            season: 赛季
            
        Returns:
            特征字典
        """
        async with AsyncSessionLocal() as db:
            features = {}
            
            # 1. 积分榜特征
            standing_features = await self._get_standing_features(
                db, home_team_id, away_team_id, league_id, season
            )
            features.update(standing_features)
            
            # 2. 近期状态特征
            recent_features = await self._get_recent_form_features(
                db, home_team_id, away_team_id, league_id, match_date
            )
            features.update(recent_features)
            
            # 3. 主客场优势特征
            home_away_features = await self._get_home_away_features(
                db, home_team_id, away_team_id, league_id, match_date
            )
            features.update(home_away_features)
            
            # 4. 对阵历史特征
            h2h_features = await self._get_head_to_head_features(
                db, home_team_id, away_team_id, league_id, match_date
            )
            features.update(h2h_features)
            
            return features
    
    async def _get_standing_features(
        self,
        db: AsyncSession,
        home_team_id: str,
        away_team_id: str,
        league_id: str,
        season: str
    ) -> Dict[str, float]:
        """提取积分榜特征"""
        features = {}
        
        # 查询主队积分榜
        stmt = select(Standing).where(
            and_(
                Standing.league_id == league_id,
                Standing.team_id == home_team_id,
                Standing.season == season
            )
        )
        result = await db.execute(stmt)
        home_standing = result.scalar_one_or_none()
        
        # 查询客队积分榜
        stmt = select(Standing).where(
            and_(
                Standing.league_id == league_id,
                Standing.team_id == away_team_id,
                Standing.season == season
            )
        )
        result = await db.execute(stmt)
        away_standing = result.scalar_one_or_none()
        
        if home_standing and away_standing:
            features["home_team_rank"] = float(home_standing.position)
            features["away_team_rank"] = float(away_standing.position)
            features["rank_diff"] = float(away_standing.position - home_standing.position)
            
            features["home_team_points"] = float(home_standing.points)
            features["away_team_points"] = float(away_standing.points)
            features["points_diff"] = float(home_standing.points - away_standing.points)
            
            features["home_team_goals_for"] = float(home_standing.goals_for)
            features["away_team_goals_for"] = float(away_standing.goals_for)
            features["home_team_goals_against"] = float(home_standing.goals_against)
            features["away_team_goals_against"] = float(away_standing.goals_against)
        else:
            # 默认值
            for key in ["home_team_rank", "away_team_rank", "rank_diff",
                       "home_team_points", "away_team_points", "points_diff",
                       "home_team_goals_for", "away_team_goals_for",
                       "home_team_goals_against", "away_team_goals_against"]:
                features[key] = 0.0
        
        return features
    
    async def _get_recent_form_features(
        self,
        db: AsyncSession,
        home_team_id: str,
        away_team_id: str,
        league_id: str,
        match_date: datetime,
        num_matches: int = 5
    ) -> Dict[str, float]:
        """提取近期状态特征（最近N场）"""
        features = {}
        
        # 主队近期战绩
        home_recent = await self._get_team_recent_results(
            db, home_team_id, league_id, match_date, num_matches
        )
        features["home_recent_wins"] = float(home_recent["wins"])
        features["home_recent_draws"] = float(home_recent["draws"])
        features["home_recent_losses"] = float(home_recent["losses"])
        
        # 客队近期战绩
        away_recent = await self._get_team_recent_results(
            db, away_team_id, league_id, match_date, num_matches
        )
        features["away_recent_wins"] = float(away_recent["wins"])
        features["away_recent_draws"] = float(away_recent["draws"])
        features["away_recent_losses"] = float(away_recent["losses"])
        
        return features
    
    async def _get_team_recent_results(
        self,
        db: AsyncSession,
        team_id: str,
        league_id: str,
        before_date: datetime,
        num_matches: int
    ) -> Dict[str, int]:
        """获取球队近期比赛结果"""
        stmt = select(Match).where(
            and_(
                Match.league_id == league_id,
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                Match.match_date < before_date,
                Match.status == "FINISHED"
            )
        ).order_by(Match.match_date.desc()).limit(num_matches)
        
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        wins = draws = losses = 0
        for match in matches:
            if match.result:
                if match.home_team_id == team_id:
                    # 主队视角
                    if match.result == "H":
                        wins += 1
                    elif match.result == "D":
                        draws += 1
                    else:
                        losses += 1
                else:
                    # 客队视角
                    if match.result == "A":
                        wins += 1
                    elif match.result == "D":
                        draws += 1
                    else:
                        losses += 1
        
        return {"wins": wins, "draws": draws, "losses": losses}
    
    async def _get_home_away_features(
        self,
        db: AsyncSession,
        home_team_id: str,
        away_team_id: str,
        league_id: str,
        match_date: datetime
    ) -> Dict[str, float]:
        """提取主客场优势特征"""
        features = {}
        
        # 主队主场胜率
        home_advantage = await self._calculate_home_win_rate(
            db, home_team_id, league_id, match_date
        )
        features["home_advantage_win_rate"] = home_advantage
        
        # 客队客场胜率
        away_disadvantage = await self._calculate_away_win_rate(
            db, away_team_id, league_id, match_date
        )
        features["away_disadvantage_win_rate"] = away_disadvantage
        
        return features
    
    async def _calculate_home_win_rate(
        self,
        db: AsyncSession,
        team_id: str,
        league_id: str,
        before_date: datetime
    ) -> float:
        """计算主场胜率"""
        stmt = select(Match).where(
            and_(
                Match.league_id == league_id,
                Match.home_team_id == team_id,
                Match.match_date < before_date,
                Match.status == "FINISHED"
            )
        )
        
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        if not matches:
            return 0.5  # 默认50%
        
        wins = sum(1 for m in matches if m.result == "H")
        return float(wins) / len(matches)
    
    async def _calculate_away_win_rate(
        self,
        db: AsyncSession,
        team_id: str,
        league_id: str,
        before_date: datetime
    ) -> float:
        """计算客场胜率"""
        stmt = select(Match).where(
            and_(
                Match.league_id == league_id,
                Match.away_team_id == team_id,
                Match.match_date < before_date,
                Match.status == "FINISHED"
            )
        )
        
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        if not matches:
            return 0.5  # 默认50%
        
        wins = sum(1 for m in matches if m.result == "A")
        return float(wins) / len(matches)
    
    async def _get_head_to_head_features(
        self,
        db: AsyncSession,
        home_team_id: str,
        away_team_id: str,
        league_id: str,
        match_date: datetime,
        num_matches: int = 10
    ) -> Dict[str, float]:
        """提取对阵历史特征"""
        features = {}
        
        # 查询历史对阵
        stmt = select(Match).where(
            and_(
                Match.league_id == league_id,
                or_(
                    and_(Match.home_team_id == home_team_id, Match.away_team_id == away_team_id),
                    and_(Match.home_team_id == away_team_id, Match.away_team_id == home_team_id)
                ),
                Match.match_date < match_date,
                Match.status == "FINISHED"
            )
        ).order_by(Match.match_date.desc()).limit(num_matches)
        
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        home_wins = draws = away_wins = 0
        for match in matches:
            if match.result:
                if match.home_team_id == home_team_id:
                    # 当前主队在历史中也是主队
                    if match.result == "H":
                        home_wins += 1
                    elif match.result == "D":
                        draws += 1
                    else:
                        away_wins += 1
                else:
                    # 当前主队在历史中是客队
                    if match.result == "A":
                        home_wins += 1
                    elif match.result == "D":
                        draws += 1
                    else:
                        away_wins += 1
        
        features["head_to_head_home_wins"] = float(home_wins)
        features["head_to_head_draws"] = float(draws)
        features["head_to_head_away_wins"] = float(away_wins)
        
        return features
    
    async def extract_training_dataset(
        self,
        league_id: Optional[str] = None,
        season: str = "2024",
        min_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        提取训练数据集
        
        Args:
            league_id: 联赛ID（None表示所有联赛）
            season: 赛季
            min_date: 最小日期（只提取此日期之后的比赛）
            
        Returns:
            DataFrame with features and labels
        """
        async with AsyncSessionLocal() as db:
            # 查询所有已完成的比赛
            conditions = [Match.status == "FINISHED", Match.result.isnot(None)]
            if league_id:
                conditions.append(Match.league_id == league_id)
            if min_date:
                conditions.append(Match.match_date >= min_date)
            
            stmt = select(Match).where(and_(*conditions)).order_by(Match.match_date)
            result = await db.execute(stmt)
            matches = result.scalars().all()
            
            print(f"找到 {len(matches)} 场已完成的比赛用于训练")
            
            # 为每场比赛提取特征
            data = []
            for i, match in enumerate(matches):
                if i % 50 == 0:
                    print(f"处理进度: {i}/{len(matches)}")
                
                try:
                    features = await self.extract_features_for_match(
                        match.home_team_id,
                        match.away_team_id,
                        match.league_id,
                        match.match_date,
                        season
                    )
                    
                    # 添加标签
                    features["label"] = match.result  # H/D/A
                    features["match_id"] = match.match_id
                    features["home_team_id"] = match.home_team_id
                    features["away_team_id"] = match.away_team_id
                    features["league_id"] = match.league_id
                    
                    data.append(features)
                except Exception as e:
                    print(f"提取特征失败 {match.match_id}: {e}")
                    continue
            
            df = pd.DataFrame(data)
            print(f"成功提取 {len(df)} 场比赛的特征")
            
            return df

