"""
检查数据库中的数据量统计
"""
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import select, func
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import League, Team, Match

async def check_counts():
    async with AsyncSessionLocal() as db:
        # 统计联赛
        result = await db.execute(select(func.count()).select_from(League))
        league_count = result.scalar()
        
        # 统计球队
        result = await db.execute(select(func.count()).select_from(Team))
        team_count = result.scalar()
        
        # 统计比赛
        result = await db.execute(select(func.count()).select_from(Match))
        match_count = result.scalar()
        
        # 按联赛统计球队
        result = await db.execute(
            select(Team.league_id, func.count()).
            group_by(Team.league_id)
        )
        teams_by_league = dict(result.fetchall())
        
        # 按联赛统计比赛
        result = await db.execute(
            select(Match.league_id, func.count()).
            group_by(Match.league_id)
        )
        matches_by_league = dict(result.fetchall())
        
        print("=" * 60)
        print("数据库统计信息")
        print("=" * 60)
        print(f"总联赛数: {league_count}")
        print(f"总球队数: {team_count}")
        print(f"总比赛数: {match_count}")
        print()
        print("按联赛统计:")
        print("-" * 60)
        for league_id, count in teams_by_league.items():
            match_count_for_league = matches_by_league.get(league_id, 0)
            print(f"  {league_id:10} - 球队: {count:3}, 比赛: {match_count_for_league:3}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_counts())

