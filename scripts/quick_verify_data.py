"""快速验证数据真实性"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match
from sqlalchemy import select

async def verify():
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("数据真实性验证")
        print("=" * 80)
        
        # 1. 检查是否还有虚假数据
        print("\n[1] 检查虚假Seed数据...")
        stmt = select(Match).where(
            Match.match_id.in_(['2024_EPL_MUN_LIV', '2024_EPL_ARS_MCI'])
        )
        result = await db.execute(stmt)
        fake_matches = result.scalars().all()
        
        if fake_matches:
            print(f"   [ERROR] 发现 {len(fake_matches)} 条虚假数据！")
            for m in fake_matches:
                print(f"      - {m.match_id}: {m.home_team_id} vs {m.away_team_id}")
        else:
            print("   [OK] 没有虚假Seed数据，数据库已清洁")
        
        # 2. 检查曼联vs利物浦在11月21日的比赛
        print("\n[2] 检查2025-11-21的曼联vs利物浦比赛...")
        from datetime import datetime, timezone
        
        date_start = datetime(2025, 11, 21, tzinfo=timezone.utc)
        date_end = datetime(2025, 11, 22, tzinfo=timezone.utc)
        
        stmt = select(Match).where(
            ((Match.home_team_id == 'MUN') & (Match.away_team_id == 'LIV')) |
            ((Match.home_team_id == 'LIV') & (Match.away_team_id == 'MUN'))
        ).where(
            Match.match_date >= date_start,
            Match.match_date < date_end
        )
        result = await db.execute(stmt)
        nov21_match = result.scalars().first()
        
        if nov21_match:
            print(f"   [ERROR] 发现11-21的比赛: {nov21_match.match_id}")
            print(f"      比分: {nov21_match.home_score}-{nov21_match.away_score}")
        else:
            print("   [OK] 11月21日没有曼联vs利物浦的比赛（正确！）")
        
        # 3. 查看曼联最近的真实比赛
        print("\n[3] 曼联最近5场真实比赛:")
        stmt = select(Match).where(
            (Match.home_team_id == 'MUN') | (Match.away_team_id == 'MUN')
        ).where(
            Match.status == "FINISHED"
        ).order_by(Match.match_date.desc()).limit(5)
        
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        for m in matches:
            has_api_tag = m.tags and 'ImportedFromAPI' in m.tags
            source = "[OK] API" if has_api_tag else "[WARN] 未知来源"
            print(f"   {m.match_date.strftime('%Y-%m-%d')}: "
                  f"{m.home_team_id} vs {m.away_team_id} "
                  f"({m.home_score}-{m.away_score}) | {source}")
        
        # 4. 统计数据来源
        print("\n[4] 数据来源统计:")
        stmt = select(Match)
        result = await db.execute(stmt)
        all_matches = result.scalars().all()
        
        api_count = sum(1 for m in all_matches if m.tags and 'ImportedFromAPI' in m.tags)
        other_count = len(all_matches) - api_count
        
        print(f"   - 来自API的真实数据: {api_count} 场")
        print(f"   - 其他来源: {other_count} 场")
        
        if other_count > 0:
            print("\n   [WARN] 警告: 存在非API来源的数据，请检查:")
            stmt = select(Match).limit(10)
            result = await db.execute(stmt)
            for m in result.scalars():
                if not m.tags or 'ImportedFromAPI' not in m.tags:
                    print(f"      - {m.match_id}: tags={m.tags}")
        else:
            print("   [OK] 所有数据均来自官方API")
        
        print("\n" + "=" * 80)
        if not fake_matches and not nov21_match and other_count == 0:
            print("[OK] 数据验证通过！所有数据均真实可靠")
        else:
            print("[ERROR] 数据验证失败，请检查上述问题")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify())

