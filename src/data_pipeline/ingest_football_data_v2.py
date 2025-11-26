"""
Football-data.org 数据摄取管道 v2.0 (企业级版本)

新增特性：
1. 自动实体对齐（使用 EntityResolver）
2. 指数退避重试机制
3. 多联赛支持
4. 增量更新策略
5. 结构化日志和监控指标
6. 数据质量检查
"""
import asyncio
import httpx
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type
)

sys.path.append(os.getcwd())

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match, League, Team
from src.shared.config import get_settings
from src.data_pipeline.schemas import ExternalApiResponse
from src.data_pipeline.entity_resolver import entity_resolver

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


class FootballDataIngester:
    """Football-data.org 数据摄取器"""
    
    def __init__(self):
        self.config = settings.service.data_source.football_data_org
        self.headers = {"X-Auth-Token": self.config.api_key}
        self.stats = {
            "total_fetched": 0,
            "successfully_ingested": 0,
            "failed_resolution": 0,
            "skipped_duplicates": 0,
            "errors": 0
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def _fetch_matches(
        self, 
        client: httpx.AsyncClient,
        league_code: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> ExternalApiResponse:
        """
        从 API 获取比赛数据（带重试机制）
        
        Args:
            client: HTTP 客户端
            league_code: 联赛代码 (PL, BL1, etc.)
            date_from: 开始日期 (ISO format)
            date_to: 结束日期 (ISO format)
            
        Returns:
            解析后的 API 响应
        """
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        
        logger.info(f"正在获取联赛 {league_code} 的比赛数据...")
        
        try:
            response = await client.get(
                f"{self.config.base_url}/competitions/{league_code}/matches",
                headers=self.headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            
            data = ExternalApiResponse(**response.json())
            logger.info(f"成功获取 {len(data.matches)} 场比赛")
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("API 速率限制，等待重试...")
                raise
            elif e.response.status_code == 403:
                logger.error("API 认证失败，请检查 API Key")
                raise
            else:
                logger.error(f"HTTP 错误: {e}")
                raise
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            raise
    
    async def _create_team(
        self, 
        db: AsyncSession, 
        team_name: str, 
        team_tla: str, 
        league_id: str
    ) -> Optional[str]:
        """
        自动创建新球队（使用 Upsert 模式避免冲突）
        
        Args:
            db: 数据库会话
            team_name: 球队全名
            team_tla: 球队简称（3字母代码）
            league_id: 所属联赛ID
            
        Returns:
            创建的球队ID，如果失败返回 None
        """
        try:
            # 生成球队ID（使用简称，如果没有则从全名生成）
            if team_tla and len(team_tla) == 3:
                team_id = team_tla.upper()
            else:
                # 从全名生成3字母代码
                words = team_name.split()
                if len(words) >= 3:
                    team_id = ''.join(w[0] for w in words[:3]).upper()
                else:
                    team_id = team_name[:3].upper()
            
            # 使用 INSERT ON CONFLICT 避免重复插入错误
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            
            stmt = pg_insert(Team).values(
                team_id=team_id,
                team_name=team_name,
                league_id=league_id
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=['team_id'])
            
            await db.execute(stmt)
            await db.flush()
            
            # 更新 EntityResolver 的缓存
            entity_resolver._team_cache[team_name.lower()] = team_id
            
            logger.info(f"创建或确认球队: {team_name} -> {team_id}")
            return team_id
            
        except Exception as e:
            logger.error(f"创建球队失败 {team_name}: {e}")
            await db.rollback()
            return None
    
    async def _validate_match_data(self, match_data: dict) -> bool:
        """
        数据质量检查
        
        Returns:
            True if valid, False otherwise
        """
        # 检查必填字段
        required_fields = ["match_id", "league_id", "home_team_id", "away_team_id", "match_date"]
        for field in required_fields:
            if not match_data.get(field):
                logger.warning(f"数据质量问题: 缺少字段 {field}")
                return False
        
        # 检查比分合理性
        if match_data.get("status") == "FINISHED":
            home_score = match_data.get("home_score")
            away_score = match_data.get("away_score")
            if home_score is None or away_score is None:
                logger.warning(f"数据质量问题: 已结束比赛缺少比分")
                return False
            if home_score < 0 or away_score < 0 or home_score > 20 or away_score > 20:
                logger.warning(f"数据质量问题: 比分异常 {home_score}:{away_score}")
                return False
        
        # 检查球队不能相同
        if match_data["home_team_id"] == match_data["away_team_id"]:
            logger.warning(f"数据质量问题: 主客队相同")
            return False
        
        return True
    
    async def ingest_league(
        self,
        league_code: str,
        incremental: bool = True,
        days_back: int = 7
    ) -> Dict[str, int]:
        """
        摄取单个联赛的数据
        
        Args:
            league_code: 联赛代码 (PL, BL1, etc.)
            incremental: 是否增量更新
            days_back: 增量更新时回溯天数
            
        Returns:
            统计信息字典
        """
        # 1. 解析联赛 ID
        league_id = await entity_resolver.resolve_league(league_code)
        if not league_id:
            logger.error(f"无法解析联赛代码: {league_code}")
            return {"error": 1}
        
        # 2. 确定时间范围（增量 vs 全量）
        date_from = None
        date_to = None
        if incremental:
            # 增量更新：只拉取最近 N 天的数据
            date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
            date_to = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
            logger.info(f"增量更新模式: {date_from} 到 {date_to}")
        
        # 3. 获取数据
        async with httpx.AsyncClient() as client:
            try:
                external_data = await self._fetch_matches(
                    client, 
                    league_code,
                    date_from,
                    date_to
                )
            except Exception as e:
                logger.error(f"获取联赛 {league_code} 数据失败: {e}")
                self.stats["errors"] += 1
                return {"error": 1}
        
        self.stats["total_fetched"] += len(external_data.matches)
        
        # 4. 处理每场比赛（每场比赛使用独立事务）
        for ext_match in external_data.matches:
            match_id = f"{league_code}_{ext_match.id}"
            try:
                # 为每场比赛创建独立的数据库会话和事务
                async with AsyncSessionLocal() as db:
                    # 4.1 实体对齐（如果球队不存在则自动创建）
                    home_id = await entity_resolver.resolve_team(
                        ext_match.homeTeam.name,
                        source="football-data.org"
                    )
                    if not home_id:
                        home_id = await self._create_team(db, ext_match.homeTeam.name, ext_match.homeTeam.tla, league_id)
                        await db.commit()
                        await entity_resolver.initialize()
                    
                    away_id = await entity_resolver.resolve_team(
                        ext_match.awayTeam.name,
                        source="football-data.org"
                    )
                    if not away_id:
                        away_id = await self._create_team(db, ext_match.awayTeam.name, ext_match.awayTeam.tla, league_id)
                        await db.commit()
                        await entity_resolver.initialize()
                    
                    if not home_id or not away_id:
                        self.stats["failed_resolution"] += 1
                        logger.warning(
                            f"跳过无法处理的比赛 {match_id}: "
                            f"{ext_match.homeTeam.name} vs {ext_match.awayTeam.name}"
                        )
                        continue
                    
                    # 4.2 状态转换
                    status = self._convert_status(ext_match.status)
                    
                    # 4.3 结果转换
                    result = None
                    if status == "FINISHED" and ext_match.score.winner:
                        result = {
                            "HOME_TEAM": "H",
                            "AWAY_TEAM": "A",
                            "DRAW": "D"
                        }.get(ext_match.score.winner)
                    
                    # 4.4 构造数据对象
                    match_data = {
                        "match_id": match_id,
                        "league_id": league_id,
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "match_date": datetime.fromisoformat(
                            ext_match.utcDate.replace("Z", "+00:00")
                        ),
                        "status": status,
                        "home_score": ext_match.score.fullTime.home,
                        "away_score": ext_match.score.fullTime.away,
                        "result": result,
                        "tags": ["ImportedFromAPI", league_code]
                    }
                    
                    # 4.5 数据质量检查
                    if not await self._validate_match_data(match_data):
                        self.stats["errors"] += 1
                        logger.warning(f"数据质量检查失败: {match_id}")
                        continue
                    
                    # 4.6 写入数据库 (Upsert)
                    stmt = insert(Match).values(match_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['match_id'],
                        set_={
                            "status": stmt.excluded.status,
                            "home_score": stmt.excluded.home_score,
                            "away_score": stmt.excluded.away_score,
                            "result": stmt.excluded.result,
                            "match_date": stmt.excluded.match_date,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    )
                    await db.execute(stmt)
                    await db.commit()
                    self.stats["successfully_ingested"] += 1
                    
            except Exception as e:
                logger.error(
                    f"处理比赛 {match_id} 失败: {e}",
                    exc_info=False
                )
                self.stats["errors"] += 1
                continue
        
        logger.info(
            f"联赛 {league_code} 数据入库完成: "
            f"成功 {self.stats['successfully_ingested']} 场 / "
            f"失败 {self.stats['errors']} 场"
        )
        
        return self.stats
    
    def _convert_status(self, external_status: str) -> str:
        """转换外部 API 的状态到内部状态"""
        status_mapping = {
            "SCHEDULED": "FIXTURE",
            "TIMED": "FIXTURE",
            "IN_PLAY": "LIVE",
            "PAUSED": "LIVE",
            "FINISHED": "FINISHED",
            "POSTPONED": "POSTPONED",
            "CANCELLED": "CANCELLED",
            "SUSPENDED": "SUSPENDED"
        }
        return status_mapping.get(external_status, "FIXTURE")
    
    async def run_full_ingestion(self, leagues: List[str] = None, days_back: int = 90):
        """
        运行完整的数据摄取流程
        
        Args:
            leagues: 要摄取的联赛列表，默认为主要联赛
            days_back: 回溯天数，默认90天
        """
        if leagues is None:
            # 默认摄取五大联赛 + 欧冠
            leagues = ["PL", "BL1", "PD", "SA", "FL1", "CL"]
        
        logger.info(f"开始数据摄取任务，目标联赛: {leagues}")
        logger.info(f"时间范围: 回溯 {days_back} 天")
        start_time = datetime.now()
        
        # 初始化实体解析器
        await entity_resolver.initialize()
        
        # 逐个联赛摄取
        for league_code in leagues:
            try:
                await self.ingest_league(
                    league_code=league_code,
                    incremental=True,
                    days_back=days_back
                )
                # 添加延迟避免API限流
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"联赛 {league_code} 摄取失败: {e}", exc_info=True)
                await asyncio.sleep(5)
                continue
        
        # 输出统计信息
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info("数据摄取任务完成！统计信息：")
        logger.info(f"  - 总获取: {self.stats['total_fetched']} 场")
        logger.info(f"  - 成功入库: {self.stats['successfully_ingested']} 场")
        logger.info(f"  - 实体解析失败: {self.stats['failed_resolution']} 场")
        logger.info(f"  - 错误: {self.stats['errors']} 场")
        logger.info(f"  - 耗时: {duration:.2f} 秒")
        logger.info("=" * 60)


async def main():
    """主函数"""
    ingester = FootballDataIngester()
    
    # 运行摄取任务
    await ingester.run_full_ingestion()


if __name__ == "__main__":
    asyncio.run(main())

