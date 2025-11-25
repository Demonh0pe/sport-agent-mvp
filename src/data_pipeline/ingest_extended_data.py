"""
扩展数据摄取脚本 - 球员、积分榜、射手榜

使用 football-data.org API 获取：
1. 球员名单 (从 /teams/{id} 端点)
2. 积分榜 (/competitions/{id}/standings)
3. 射手榜 (/competitions/{id}/scorers)

使用方法:
    python src/data_pipeline/ingest_extended_data.py
"""
import asyncio
import httpx
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

sys.path.append(os.getcwd())

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Team
from src.shared.config import get_settings
import logging

# 注意：这里需要先将 models_extended.py 中的模型添加到 models.py，然后再导入
from src.infra.db.models import Standing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class ExtendedDataIngester:
    """扩展数据摄取器"""
    
    def __init__(self):
        self.config = settings.service.data_source.football_data_org
        self.headers = {"X-Auth-Token": self.config.api_key}
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    # ==========================================
    # 1. 积分榜数据摄取
    # ==========================================
    
    async def fetch_standings(self, competition_code: str, season: int = 2024) -> Dict:
        """
        获取积分榜数据
        
        API 端点: GET /competitions/{id}/standings
        响应结构:
        {
            "standings": [
                {
                    "stage": "REGULAR_SEASON",
                    "type": "TOTAL",
                    "table": [
                        {
                            "position": 1,
                            "team": { "id": 65, "name": "Manchester City FC", ... },
                            "playedGames": 12,
                            "won": 9,
                            "draw": 2,
                            "lost": 1,
                            "points": 29,
                            "goalsFor": 28,
                            "goalsAgainst": 10,
                            "goalDifference": 18
                        },
                        ...
                    ]
                }
            ],
            "season": { "id": 2024, ... }
        }
        """
        url = f"{self.config.base_url}/competitions/{competition_code}/standings"
        logger.info(f"获取 {competition_code} 积分榜...")
        
        try:
            response = await self.client.get(url, params={"season": season})
            response.raise_for_status()
            data = response.json()
            logger.info(f"成功获取积分榜数据")
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error("API Key 无效或权限不足")
            elif e.response.status_code == 404:
                logger.warning(f"联赛 {competition_code} 无积分榜数据")
            raise
    
    async def ingest_standings(self, competition_code: str, season: int = 2024):
        """
        将积分榜数据写入数据库
        
        注意：需要先在 models.py 中添加 Standing 模型，并运行 alembic migration
        """
        standings_data = await self.fetch_standings(competition_code, season)
        
        # 解析联赛 ID
        league_id_map = {
            "PL": "EPL", "BL1": "BL1", "PD": "PD", 
            "SA": "SA", "FL1": "FL1", "CL": "UCL"
        }
        league_id = league_id_map.get(competition_code, competition_code)
        
        async with AsyncSessionLocal() as db:
            for standing_group in standings_data.get("standings", []):
                if standing_group["type"] != "TOTAL":
                    continue  # 只处理总积分榜，跳过主场/客场分榜
                
                for entry in standing_group["table"]:
                    team_name = entry["team"]["name"]
                    
                    # 实体对齐：将 API 球队名称映射到内部 team_id
                    # 这里简化处理，使用球队 TLA（3字母代码）
                    team_tla = entry["team"].get("tla", "UNK")
                    team_id = team_tla.upper()
                    
                    # 确保球队存在（如果不存在则创建）
                    existing_team = await db.execute(select(Team).where(Team.team_id == team_id))
                    if not existing_team.scalar_one_or_none():
                        new_team = Team(
                            team_id=team_id,
                            team_name=team_name,
                            league_id=league_id
                        )
                        db.add(new_team)
                        await db.flush()
                        logger.info(f"  创建球队: {team_name} ({team_id})")
                    
                    standing_data = {
                        "league_id": league_id,
                        "team_id": team_id,
                        "season": str(season),
                        "position": entry["position"],
                        "played_games": entry["playedGames"],
                        "won": entry["won"],
                        "draw": entry["draw"],
                        "lost": entry["lost"],
                        "goals_for": entry["goalsFor"],
                        "goals_against": entry["goalsAgainst"],
                        "goal_difference": entry["goalDifference"],
                        "points": entry["points"],
                        # "form": entry.get("form")  # 有些 API 包含近期战绩，如 "WWDLW"
                    }
                    
                    # Upsert 操作（如果存在则更新）
                    stmt = insert(Standing).values(standing_data)
                    stmt = stmt.on_conflict_do_nothing()
                    await db.execute(stmt)
                    
                    logger.info(f"  {entry['position']:2}. {team_name:30} - {entry['points']} 分")
            
            await db.commit()
            logger.info(f"✅ {competition_code} 积分榜数据入库完成")
    
    # ==========================================
    # 2. 球员数据摄取
    # ==========================================
    
    async def fetch_team_squad(self, team_id: int) -> Dict:
        """
        获取球队阵容（球员名单）
        
        API 端点: GET /teams/{id}
        响应结构:
        {
            "id": 65,
            "name": "Manchester City FC",
            "shortName": "Man City",
            "tla": "MCI",
            "coach": {
                "id": 123,
                "name": "Pep Guardiola",
                "nationality": "Spain"
            },
            "squad": [
                {
                    "id": 3332,
                    "name": "Erling Haaland",
                    "position": "Centre-Forward",
                    "dateOfBirth": "2000-07-21",
                    "nationality": "Norway"
                },
                ...
            ]
        }
        """
        url = f"{self.config.base_url}/teams/{team_id}"
        logger.info(f"获取球队 {team_id} 的阵容...")
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            logger.info(f"成功获取球队 {data['name']} 的阵容，共 {len(data.get('squad', []))} 名球员")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"获取球队 {team_id} 失败: {e}")
            raise
    
    async def ingest_team_squad(self, team_id: int, internal_team_id: str):
        """
        将球队阵容数据写入数据库
        
        注意：需要先在 models.py 中添加 Player 模型，并运行 alembic migration
        """
        team_data = await self.fetch_team_squad(team_id)
        
        async with AsyncSessionLocal() as db:
            for player_entry in team_data.get("squad", []):
                # 位置映射
                position_map = {
                    "Goalkeeper": "GK",
                    "Defence": "DF",
                    "Midfield": "MF",
                    "Offence": "FW",
                    "Centre-Forward": "FW",
                    "Attacking Midfield": "MF",
                    "Defensive Midfield": "MF",
                    "Left-Back": "DF",
                    "Right-Back": "DF",
                    "Centre-Back": "DF",
                }
                position = position_map.get(player_entry.get("position", ""), "UNK")
                
                # 解析生日
                dob_str = player_entry.get("dateOfBirth")
                date_of_birth = None
                if dob_str:
                    try:
                        date_of_birth = datetime.fromisoformat(dob_str)
                    except:
                        pass
                
                player_data = {
                    "player_id": f"P{player_entry['id']}",  # 添加前缀避免与其他 ID 冲突
                    "player_name": player_entry["name"],
                    "team_id": internal_team_id,
                    "position": position,
                    "nationality": player_entry.get("nationality"),
                    "date_of_birth": date_of_birth,
                    "shirt_number": player_entry.get("shirtNumber"),
                }
                
                # Upsert 操作
                # stmt = insert(Player).values(player_data)
                # stmt = stmt.on_conflict_do_update(
                #     index_elements=['player_id'],
                #     set_={
                #         "player_name": stmt.excluded.player_name,
                #         "team_id": stmt.excluded.team_id,
                #         "position": stmt.excluded.position,
                #         "nationality": stmt.excluded.nationality,
                #         "shirt_number": stmt.excluded.shirt_number,
                #     }
                # )
                # await db.execute(stmt)
                
                logger.info(f"  {player_entry.get('shirtNumber', '--'):2} | {player_entry['name']:30} | {position}")
            
            # await db.commit()
            logger.info(f"✅ 球队 {team_data['name']} 的阵容数据入库完成")
    
    # ==========================================
    # 3. 射手榜数据摄取
    # ==========================================
    
    async def fetch_scorers(self, competition_code: str, season: int = 2024, limit: int = 20) -> Dict:
        """
        获取射手榜数据
        
        API 端点: GET /competitions/{id}/scorers
        响应结构:
        {
            "scorers": [
                {
                    "player": {
                        "id": 3332,
                        "name": "Erling Haaland",
                        "nationality": "Norway",
                        "position": "Attacker"
                    },
                    "team": { "id": 65, "name": "Manchester City FC" },
                    "goals": 14,
                    "assists": 3,
                    "penalties": 2
                },
                ...
            ]
        }
        """
        url = f"{self.config.base_url}/competitions/{competition_code}/scorers"
        logger.info(f"获取 {competition_code} 射手榜 (Top {limit})...")
        
        try:
            response = await self.client.get(url, params={"season": season, "limit": limit})
            response.raise_for_status()
            data = response.json()
            logger.info(f"成功获取射手榜数据，共 {len(data.get('scorers', []))} 名球员")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"获取射手榜失败: {e}")
            raise
    
    async def ingest_scorers(self, competition_code: str, season: int = 2024, limit: int = 20):
        """
        将射手榜数据写入 PlayerSeasonStats 表
        
        注意：需要先在 models.py 中添加 PlayerSeasonStats 模型，并运行 alembic migration
        """
        scorers_data = await self.fetch_scorers(competition_code, season, limit)
        
        league_id_map = {
            "PL": "EPL", "BL1": "BL1", "PD": "PD", 
            "SA": "SA", "FL1": "FL1", "CL": "UCL"
        }
        league_id = league_id_map.get(competition_code, competition_code)
        
        async with AsyncSessionLocal() as db:
            for rank, entry in enumerate(scorers_data.get("scorers", []), start=1):
                player_info = entry["player"]
                team_info = entry["team"]
                
                player_id = f"P{player_info['id']}"
                team_tla = team_info.get("tla", "UNK")
                team_id = team_tla.upper()
                
                stats_data = {
                    "player_id": player_id,
                    "season": str(season),
                    "league_id": league_id,
                    "team_id": team_id,
                    "goals": entry.get("goals", 0),
                    "assists": entry.get("assists", 0),
                    # 其他字段可以从其他 API 补充
                }
                
                # Upsert 操作
                # stmt = insert(PlayerSeasonStats).values(stats_data)
                # stmt = stmt.on_conflict_do_update(
                #     index_elements=['player_id', 'season', 'league_id'],
                #     set_={
                #         "goals": stmt.excluded.goals,
                #         "assists": stmt.excluded.assists,
                #     }
                # )
                # await db.execute(stmt)
                
                logger.info(f"  {rank:2}. {player_info['name']:30} | {entry['goals']:2} 球 | {entry.get('assists', 0):2} 助")
            
            # await db.commit()
            logger.info(f"✅ {competition_code} 射手榜数据入库完成")


# ==========================================
# 主函数：演示数据摄取流程
# ==========================================

async def main():
    """
    摄取所有联赛的积分榜数据
    """
    ingester = ExtendedDataIngester()
    
    # 支持的联赛列表
    leagues = [
        ("PL", "英超"),
        ("BL1", "德甲"),
        ("PD", "西甲"),
        ("SA", "意甲"),
        ("FL1", "法甲"),
    ]
    
    total_success = 0
    total_failed = 0
    
    try:
        for competition_code, league_name in leagues:
            logger.info("\n" + "=" * 60)
            logger.info(f"摄取 {league_name} ({competition_code}) 积分榜数据")
            logger.info("=" * 60)
            try:
                await ingester.ingest_standings(competition_code, season=2024)
                total_success += 1
                # 避免触发 API 速率限制
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"摄取 {league_name} 失败: {e}")
                total_failed += 1
                await asyncio.sleep(5)  # 如果失败，等待更久
        
        logger.info("\n" + "=" * 60)
        logger.info("所有联赛积分榜摄取完成")
        logger.info(f"成功: {total_success} 个联赛")
        logger.info(f"失败: {total_failed} 个联赛")
        logger.info("=" * 60)
        
    finally:
        await ingester.close()


if __name__ == "__main__":
    asyncio.run(main())

