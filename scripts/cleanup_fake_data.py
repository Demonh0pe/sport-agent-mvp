"""
数据清理脚本 - 删除虚假的Seed数据

目的: 清理数据库中不真实的测试数据，避免与真实API数据混淆
"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from sqlalchemy import select, delete
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match
from datetime import datetime

async def cleanup_fake_data():
    """清理虚假的Seed数据"""
    
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("数据清理 - 删除虚假Seed数据")
        print("=" * 80)
        
        # 1. 查找所有Seed数据
        print("\n1. 检查现有Seed数据...")
        
        stmt = select(Match).where(
            Match.match_id.in_(['2024_EPL_MUN_LIV', '2024_EPL_ARS_MCI'])
        )
        result = await db.execute(stmt)
        seed_matches = result.scalars().all()
        
        if not seed_matches:
            print("   ✅ 未发现Seed数据，数据库已清洁。")
            return
        
        print(f"   ⚠️  发现 {len(seed_matches)} 条Seed数据:")
        for match in seed_matches:
            print(f"      - {match.match_id}: {match.home_team_id} vs {match.away_team_id}")
            print(f"        日期: {match.match_date}")
            print(f"        标签: {match.tags}")
        
        # 2. 自动执行删除（非交互式）
        print("\n2. 准备删除虚假数据...")
        print("   ⚠️  正在自动删除...")
        
        # 3. 执行删除
        delete_stmt = delete(Match).where(
            Match.match_id.in_(['2024_EPL_MUN_LIV', '2024_EPL_ARS_MCI'])
        )
        
        result = await db.execute(delete_stmt)
        await db.commit()
        
        print(f"   ✅ 成功删除 {result.rowcount} 条虚假数据")
        
        # 4. 验证清理结果
        print("\n3. 验证清理结果...")
        stmt = select(Match).where(
            Match.match_id.in_(['2024_EPL_MUN_LIV', '2024_EPL_ARS_MCI'])
        )
        result = await db.execute(stmt)
        remaining = result.scalars().all()
        
        if not remaining:
            print("   ✅ 验证通过：虚假数据已完全清除")
        else:
            print(f"   ❌ 警告：仍有 {len(remaining)} 条数据残留")
        
        # 5. 显示清理后的曼联比赛数据
        print("\n4. 清理后的曼联比赛数据 (最近5场):")
        stmt = select(Match).where(
            (Match.home_team_id == 'MUN') | (Match.away_team_id == 'MUN')
        ).order_by(Match.match_date.desc()).limit(5)
        
        result = await db.execute(stmt)
        matches = result.scalars().all()
        
        for m in matches:
            score = f"{m.home_score}-{m.away_score}" if m.status == "FINISHED" else "未开赛"
            tags = m.tags if m.tags else []
            source = "API" if "ImportedFromAPI" in tags else "未知"
            print(f"   - {m.match_date.strftime('%Y-%m-%d')}: {m.home_team_id} vs {m.away_team_id} | "
                  f"{score} | 来源: {source}")
        
        print("\n" + "=" * 80)
        print("数据清理完成!")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(cleanup_fake_data())

