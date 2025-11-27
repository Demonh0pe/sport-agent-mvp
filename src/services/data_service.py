"""
DataService - 数据访问服务层

职责：
1. 封装所有与比赛/球队/联赛相关的数据访问
2. 统一处理名称映射（别名 → 标准 ID）
3. 本地 DB 查询
4. 必要时调用 football-data API 回源

注意：
- 纯 Python 实现，不依赖 LangChain
- 可被 Tools、Agents、Scripts 复用
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from src.infra.db.models import League, Team, Match, Standing
from src.infra.db.session import get_async_session
from src.data_pipeline.entity_resolver import entity_resolver
from src.services.config import data_config

logger = logging.getLogger(__name__)


class DataService:
    """
    数据访问服务
    
    设计原则：
    - 所有数据访问通过此服务统一入口
    - 支持异步操作
    - 自动处理实体解析（别名 → 标准ID）
    - 提供缓存友好的查询接口
    """
    
    def __init__(self):
        self._entity_resolver = entity_resolver
        self._resolver_initialized = False
        self._config = data_config
    
    async def _ensure_resolver_initialized(self):
        """确保 EntityResolver 已初始化"""
        if not self._resolver_initialized:
            await self._entity_resolver.initialize()
            self._resolver_initialized = True
            logger.info("EntityResolver initialized")
    
    # ==================== 联赛相关 ====================
    
    async def get_competitions(self) -> List[League]:
        """
        获取所有可用的联赛列表
        
        Returns:
            联赛列表
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(League).order_by(League.league_name)
            )
            return list(result.scalars().all())
    
    async def get_competition(
        self, 
        competition_name_or_id: str
    ) -> Optional[League]:
        """
        获取单个联赛信息
        
        Args:
            competition_name_or_id: 联赛名称或 ID
            
        Returns:
            联赛对象，未找到返回 None
        """
        async with get_async_session() as session:
            # 按名称或ID查询
            result = await session.execute(
                select(League).where(
                    or_(
                        League.league_id == competition_name_or_id,
                        League.league_name.ilike(f"%{competition_name_or_id}%")
                    )
                )
            )
            return result.scalar_one_or_none()
    
    # ==================== 球队相关 ====================
    
    async def get_team(
        self, 
        team_name_or_id: str
    ) -> Optional[Team]:
        """
        获取球队信息（支持别名解析）
        
        Args:
            team_name_or_id: 球队名称、别名或 ID
            
        Returns:
            球队对象，未找到返回 None
        """
        await self._ensure_resolver_initialized()
        
        async with get_async_session() as session:
            # 尝试按 ID 查询
            result = await session.execute(
                select(Team).where(Team.team_id == team_name_or_id)
            )
            team = result.scalar_one_or_none()
            if team:
                return team
            
            # 使用 EntityResolver 解析别名
            team_id = await self._entity_resolver.resolve_team(
                team_name_or_id, 
                source="data_service",
                fuzzy_threshold=self._config.DEFAULT_FUZZY_THRESHOLD
            )
            
            if team_id:
                result = await session.execute(
                    select(Team).where(Team.team_id == team_id)
                )
                return result.scalar_one_or_none()
            
            # 如果 EntityResolver 未找到，尝试直接模糊匹配
            result = await session.execute(
                select(Team).where(
                    Team.team_name.ilike(f"%{team_name_or_id}%")
                ).limit(1)
            )
            return result.scalar_one_or_none()
    
    async def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """
        按 ID 获取球队信息
        
        Args:
            team_id: 球队 ID (字符串)
            
        Returns:
            球队对象
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(Team).where(Team.team_id == team_id)
            )
            return result.scalar_one_or_none()
    
    # ==================== 比赛相关 ====================
    
    async def get_matches(
        self,
        competition: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        team_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Match]:
        """
        查询比赛列表
        
        Args:
            competition: 联赛名称或代码
            date_from: 开始日期
            date_to: 结束日期
            team_name: 球队名称（主队或客队）
            status: 比赛状态 (SCHEDULED/FINISHED/POSTPONED 等)
            limit: 返回数量限制
            
        Returns:
            比赛列表
        """
        # 使用默认限制或配置的最大限制
        if limit is None:
            limit = self._config.DEFAULT_MATCH_LIMIT
        else:
            limit = min(limit, self._config.MAX_MATCH_LIMIT)
        
        async with get_async_session() as session:
            query = select(Match).options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
                selectinload(Match.competition)
            )
            
            filters = []
            
            # 联赛过滤
            if competition:
                comp = await self.get_competition(competition)
                if comp:
                    filters.append(Match.league_id == comp.league_id)
            
            # 日期过滤
            if date_from:
                filters.append(Match.match_date >= date_from)
            if date_to:
                filters.append(Match.match_date <= date_to)
            
            # 球队过滤
            if team_name:
                team = await self.get_team(team_name)
                if team:
                    filters.append(
                        or_(
                            Match.home_team_id == team.team_id,
                            Match.away_team_id == team.team_id
                        )
                    )
            
            # 状态过滤
            if status:
                filters.append(Match.status == status)
            
            if filters:
                query = query.where(and_(*filters))
            
            query = query.order_by(desc(Match.match_date)).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_match(self, match_id: str) -> Optional[Match]:
        """
        获取单场比赛详情
        
        Args:
            match_id: 比赛 ID (字符串)
            
        Returns:
            比赛对象
        """
        async with get_async_session() as session:
            result = await session.execute(
                select(Match)
                .where(Match.match_id == match_id)
            )
            return result.scalar_one_or_none()
    
    async def get_recent_matches(
        self,
        team_name: str,
        last_n: int = 10,
        before_date: Optional[date] = None
    ) -> List[Match]:
        """
        获取球队最近 N 场比赛
        
        Args:
            team_name: 球队名称
            last_n: 最近场次数
            before_date: 截止日期（不包含该日期之后的比赛）
            
        Returns:
            比赛列表（按时间倒序，包含关联球队信息）
        """
        from sqlalchemy.orm import selectinload
        
        team = await self.get_team(team_name)
        if not team:
            logger.warning(f"Team not found: {team_name}")
            return []
        
        async with get_async_session() as session:
            query = select(Match).options(
                selectinload(Match.home_team),  # 预加载主队信息
                selectinload(Match.away_team)   # 预加载客队信息
            ).where(
                and_(
                    or_(
                        Match.home_team_id == team.team_id,
                        Match.away_team_id == team.team_id
                    ),
                    Match.status == "FINISHED"
                )
            )
            
            if before_date:
                query = query.where(Match.match_date < before_date)
            
            query = query.order_by(desc(Match.match_date)).limit(last_n)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    # ==================== 积分榜相关 ====================
    
    async def get_standings(
        self,
        competition: str,
        season: Optional[str] = None
    ) -> List[Standing]:
        """
        获取联赛积分榜
        
        Args:
            competition: 联赛名称或代码
            season: 赛季（如 "2024"），默认当前赛季
            
        Returns:
            积分榜列表（按排名排序，包含关联球队信息）
        """
        from sqlalchemy.orm import selectinload
        
        comp = await self.get_competition(competition)
        if not comp:
            logger.warning(f"Competition not found: {competition}")
            return []
        
        async with get_async_session() as session:
            query = select(Standing).options(
                selectinload(Standing.team)  # 预加载球队信息
            ).where(Standing.league_id == comp.league_id)
            
            if season:
                query = query.where(Standing.season == season)
            
            query = query.order_by(Standing.position)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_team_standing(
        self,
        team_name: str,
        competition: Optional[str] = None
    ) -> Optional[Standing]:
        """
        获取球队在联赛中的积分榜位置
        
        Args:
            team_name: 球队名称
            competition: 联赛名称（可选，如不提供则返回主要联赛排名）
            
        Returns:
            积分榜记录
        """
        team = await self.get_team(team_name)
        if not team:
            logger.warning(f"Team not found: {team_name}")
            return None
        
        async with get_async_session() as session:
            query = select(Standing).where(Standing.team_id == team.team_id)
            
            if competition:
                comp = await self.get_competition(competition)
                if comp:
                    query = query.where(Standing.league_id == comp.league_id)
            
            query = query.order_by(desc(Standing.updated_at)).limit(1)
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    # ==================== 统计辅助方法 ====================
    
    async def get_head_to_head(
        self,
        team_a_name: str,
        team_b_name: str,
        last_n: int = 10
    ) -> List[Match]:
        """
        获取两队历史交锋记录
        
        Args:
            team_a_name: 球队A名称
            team_b_name: 球队B名称
            last_n: 最近场次数
            
        Returns:
            比赛列表
        """
        team_a = await self.get_team(team_a_name)
        team_b = await self.get_team(team_b_name)
        
        if not team_a or not team_b:
            logger.warning(f"Team not found: {team_a_name} or {team_b_name}")
            return []
        
        async with get_async_session() as session:
            query = select(Match).where(
                and_(
                    Match.status == "FINISHED",
                    or_(
                        and_(
                            Match.home_team_id == team_a.team_id,
                            Match.away_team_id == team_b.team_id
                        ),
                        and_(
                            Match.home_team_id == team_b.team_id,
                            Match.away_team_id == team_a.team_id
                        )
                    )
                )
            ).order_by(desc(Match.match_date)).limit(last_n)
            
            result = await session.execute(query)
            return list(result.scalars().all())


# 全局单例
data_service = DataService()

