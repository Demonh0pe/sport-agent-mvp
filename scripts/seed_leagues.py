"""
补充缺失的联赛数据
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.dialects.postgresql import insert
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import League

LEAGUES = [
    {"league_id": "EPL", "league_name": "英格兰超级联赛", "country": "England", "level": 1},
    {"league_id": "UCL", "league_name": "欧洲冠军联赛", "country": "Europe", "level": 1},
    {"league_id": "BL1", "league_name": "德国甲级联赛", "country": "Germany", "level": 1},
    {"league_id": "PD", "league_name": "西班牙甲级联赛", "country": "Spain", "level": 1},
    {"league_id": "SA", "league_name": "意大利甲级联赛", "country": "Italy", "level": 1},
    {"league_id": "FL1", "league_name": "法国甲级联赛", "country": "France", "level": 1},
]

async def seed_leagues():
    async with AsyncSessionLocal() as db:
        for league_data in LEAGUES:
            stmt = insert(League).values(league_data)
            stmt = stmt.on_conflict_do_nothing(index_elements=['league_id'])
            await db.execute(stmt)
        
        await db.commit()
        print(f"成功添加/更新 {len(LEAGUES)} 个联赛！")

if __name__ == "__main__":
    asyncio.run(seed_leagues())

