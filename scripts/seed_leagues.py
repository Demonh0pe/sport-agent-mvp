#!/usr/bin/env python3
"""插入基础联赛数据"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.infra.db.session import AsyncSessionLocal


async def seed_leagues():
    """插入基础联赛信息"""
    print("开始插入基础联赛数据...")
    
    async with AsyncSessionLocal() as db:
        # 插入联赛
        await db.execute(text("""
            INSERT INTO leagues (league_id, league_name, country, level) VALUES
            ('PL', 'Premier League (英超)', 'England', 1),
            ('BL1', 'Bundesliga (德甲)', 'Germany', 1),
            ('PD', 'La Liga (西甲)', 'Spain', 1),
            ('SA', 'Serie A (意甲)', 'Italy', 1),
            ('FL1', 'Ligue 1 (法甲)', 'France', 1),
            ('CL', 'UEFA Champions League (欧冠)', 'Europe', 1)
            ON CONFLICT (league_id) DO NOTHING
        """))
        
        await db.commit()
        
        # 检查结果
        result = await db.execute(text("SELECT league_id, league_name FROM leagues ORDER BY league_id"))
        leagues = result.all()
        
        print(f"\n[OK] 成功插入 {len(leagues)} 个联赛:")
        for league_id, league_name in leagues:
            print(f"  - {league_id}: {league_name}")
        
    print("\n完成！现在可以运行数据导入了:")
    print("  python src/data_pipeline/ingest_football_data_v2.py")


if __name__ == "__main__":
    asyncio.run(seed_leagues())

