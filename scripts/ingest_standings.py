"""
导入联赛积分榜数据

从 football-data.org API 获取积分榜并存入数据库
"""
import asyncio
import httpx
import sys
import os
from datetime import datetime

sys.path.append(os.getcwd())

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Standing, League, Team
from src.shared.config import get_settings

settings = get_settings()


async def fetch_and_save_standings(league_code: str):
    """获取并保存某个联赛的积分榜"""
    
    config = settings.service.data_source.football_data_org
    headers = {"X-Auth-Token": config.api_key}
    
    async with httpx.AsyncClient() as client:
        print(f"\n正在获取 {league_code} 积分榜...")
        
        try:
            # 1. 调用 API 获取积分榜
            response = await client.get(
                f"{config.base_url}/competitions/{league_code}/standings",
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # 2. 解析数据
            standings_data = data.get("standings", [])
            if not standings_data:
                print(f"  ⚠️  {league_code} 没有积分榜数据")
                return 0
            
            # 通常第一个是总积分榜（TOTAL），还有主场/客场积分榜
            total_standings = None
            for standing_group in standings_data:
                if standing_group.get("type") == "TOTAL":
                    total_standings = standing_group
                    break
            
            if not total_standings:
                total_standings = standings_data[0]  # 使用第一个
            
            table = total_standings.get("table", [])
            season_year = data.get("season", {}).get("startDate", "")[:4]
            
            # 3. 保存到数据库
            async with AsyncSessionLocal() as session:
                saved_count = 0
                
                for entry in table:
                    team_data = entry.get("team", {})
                    team_name = team_data.get("name", "")
                    team_id = team_data.get("id")
                    
                    # 查找球队（通过名称模糊匹配）
                    stmt = select(Team).where(Team.team_name.ilike(f"%{team_name}%"))
                    result = await session.execute(stmt)
                    team = result.scalar_one_or_none()
                    
                    if not team:
                        print(f"  ⚠️  找不到球队: {team_name}")
                        continue
                    
                    # 先删除旧记录，再插入新记录（简单策略）
                    from sqlalchemy import delete
                    
                    # 删除旧记录
                    delete_stmt = delete(Standing).where(
                        Standing.league_id == league_code,
                        Standing.team_id == team.team_id,
                        Standing.season == season_year
                    )
                    await session.execute(delete_stmt)
                    
                    # 插入新记录
                    standing = Standing(
                        league_id=league_code,
                        team_id=team.team_id,
                        team_name=team.team_name,
                        season=season_year,
                        position=entry.get("position"),
                        played_games=entry.get("playedGames", 0),
                        won=entry.get("won", 0),
                        draw=entry.get("draw", 0),
                        lost=entry.get("lost", 0),
                        goals_for=entry.get("goalsFor", 0),
                        goals_against=entry.get("goalsAgainst", 0),
                        goal_difference=entry.get("goalDifference", 0),
                        points=entry.get("points", 0),
                    )
                    session.add(standing)
                    saved_count += 1
                
                await session.commit()
                print(f"  ✅ {league_code} 积分榜保存成功: {saved_count} 支球队")
                return saved_count
                
        except httpx.HTTPStatusError as e:
            print(f"  ❌ API 错误: {e.response.status_code} - {e.response.text}")
            return 0
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            return 0


async def main():
    """导入所有主要联赛的积分榜"""
    
    print("="*70)
    print("导入联赛积分榜数据")
    print("="*70)
    
    leagues = ["PL", "BL1", "PD", "SA", "FL1"]
    league_names = {
        "PL": "英超",
        "BL1": "德甲",
        "PD": "西甲",
        "SA": "意甲",
        "FL1": "法甲",
    }
    
    total_saved = 0
    
    for league_code in leagues:
        count = await fetch_and_save_standings(league_code)
        total_saved += count
        await asyncio.sleep(3)  # 避免 API 限流
    
    print("\n" + "="*70)
    print(f"✅ 完成！共导入 {total_saved} 条积分榜记录")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())

