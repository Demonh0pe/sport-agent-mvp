"""
数据检查工具 - 详细查看API获取的数据

用法: python scripts/inspect_data.py [选项]
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.append(os.getcwd())

from sqlalchemy import select, func
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match, Team, League, Standing


async def inspect_recent_matches():
    """查看最近的比赛，包含详细信息"""
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 100)
        print("📊 最近20场比赛详细信息")
        print("=" * 100)
        
        # 获取比赛和球队信息
        stmt = (
            select(Match, Team.team_name, League.league_name)
            .join(Team, Match.home_team_id == Team.team_id)
            .join(League, Match.league_id == League.league_id)
            .order_by(Match.match_date.desc())
            .limit(20)
        )
        
        result = await db.execute(stmt)
        matches = result.all()
        
        print(f"\n{'日期':<12} {'联赛':<15} {'主队':<25} {'比分':<8} {'客队':<25} {'状态':<12} {'来源':<10}")
        print("-" * 120)
        
        for match, home_team_name, league_name in matches:
            # 获取客队名称
            away_stmt = select(Team.team_name).where(Team.team_id == match.away_team_id)
            away_result = await db.execute(away_stmt)
            away_team_name = away_result.scalar()
            
            date_str = match.match_date.strftime("%Y-%m-%d") if match.match_date else "N/A"
            score = f"{match.home_score or '?'}:{match.away_score or '?'}"
            
            # 检查数据来源
            source = "✅ API" if match.tags and 'ImportedFromAPI' in match.tags else "❌ 未知"
            
            # 状态颜色标记
            status_display = {
                "FINISHED": "✅ 已完成",
                "FIXTURE": "⏰ 未开始",
                "LIVE": "🔴 进行中",
                "POSTPONED": "⏸️  延期",
                "CANCELLED": "❌ 取消"
            }.get(match.status, match.status)
            
            print(f"{date_str:<12} {league_name[:12]:<15} {home_team_name[:22]:<25} "
                  f"{score:^8} {away_team_name[:22]:<25} {status_display:<12} {source:<10}")
        
        print("=" * 100)


async def inspect_data_by_league():
    """按联赛统计数据质量"""
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("📋 各联赛数据统计")
        print("=" * 80)
        
        # 获取所有联赛
        leagues_stmt = select(League)
        leagues_result = await db.execute(leagues_stmt)
        leagues = leagues_result.scalars().all()
        
        print(f"\n{'联赛':<20} {'总比赛':<10} {'已完成':<10} {'未来赛程':<12} {'API数据':<10} {'数据完整度':<10}")
        print("-" * 90)
        
        for league in leagues:
            # 总比赛数
            total_stmt = select(func.count()).select_from(Match).where(
                Match.league_id == league.league_id
            )
            total_result = await db.execute(total_stmt)
            total_matches = total_result.scalar()
            
            # 已完成比赛
            finished_stmt = select(func.count()).select_from(Match).where(
                Match.league_id == league.league_id,
                Match.status == "FINISHED"
            )
            finished_result = await db.execute(finished_stmt)
            finished_matches = finished_result.scalar()
            
            # 未来赛程
            fixture_stmt = select(func.count()).select_from(Match).where(
                Match.league_id == league.league_id,
                Match.status == "FIXTURE"
            )
            fixture_result = await db.execute(fixture_stmt)
            fixture_matches = fixture_result.scalar()
            
            # API来源数据
            all_matches_stmt = select(Match).where(Match.league_id == league.league_id)
            all_matches_result = await db.execute(all_matches_stmt)
            all_matches = all_matches_result.scalars().all()
            api_matches = sum(1 for m in all_matches if m.tags and 'ImportedFromAPI' in m.tags)
            
            # 数据完整度（API数据占比）
            completeness = f"{(api_matches/total_matches*100):.1f}%" if total_matches > 0 else "N/A"
            
            print(f"{league.league_name[:18]:<20} {total_matches:<10} {finished_matches:<10} "
                  f"{fixture_matches:<12} {api_matches:<10} {completeness:<10}")
        
        print("=" * 80)


async def inspect_specific_match(match_id: str = None):
    """检查特定比赛的详细信息"""
    async with AsyncSessionLocal() as db:
        if not match_id:
            # 如果没有指定，显示最近的一场完成的比赛
            stmt = (
                select(Match)
                .where(Match.status == "FINISHED")
                .order_by(Match.match_date.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            match = result.scalar_one_or_none()
        else:
            stmt = select(Match).where(Match.match_id == match_id)
            result = await db.execute(stmt)
            match = result.scalar_one_or_none()
        
        if not match:
            print(f"\n❌ 未找到比赛: {match_id}")
            return
        
        print("\n" + "=" * 80)
        print("🔍 比赛详细信息")
        print("=" * 80)
        
        # 获取球队和联赛信息
        home_stmt = select(Team).where(Team.team_id == match.home_team_id)
        home_result = await db.execute(home_stmt)
        home_team = home_result.scalar_one_or_none()
        
        away_stmt = select(Team).where(Team.team_id == match.away_team_id)
        away_result = await db.execute(away_stmt)
        away_team = away_result.scalar_one_or_none()
        
        league_stmt = select(League).where(League.league_id == match.league_id)
        league_result = await db.execute(league_stmt)
        league = league_result.scalar_one_or_none()
        
        print(f"\n比赛ID:      {match.match_id}")
        print(f"联赛:        {league.league_name if league else match.league_id}")
        print(f"主队:        {home_team.team_name if home_team else match.home_team_id} (ID: {match.home_team_id})")
        print(f"客队:        {away_team.team_name if away_team else match.away_team_id} (ID: {match.away_team_id})")
        print(f"比分:        {match.home_score} - {match.away_score}")
        print(f"比赛时间:    {match.match_date}")
        print(f"状态:        {match.status}")
        print(f"结果:        {match.result or 'N/A'}")
        print(f"标签:        {match.tags or []}")
        print(f"创建时间:    {match.created_at}")
        print(f"更新时间:    {match.updated_at}")
        
        # 数据来源判断
        is_api_data = match.tags and 'ImportedFromAPI' in match.tags
        print(f"\n数据来源:    {'✅ 官方API (football-data.org)' if is_api_data else '❌ 未知来源（需检查）'}")
        
        # 数据质量检查
        print("\n数据质量检查:")
        checks = []
        checks.append(("✅" if match.match_id else "❌", "比赛ID存在"))
        checks.append(("✅" if match.league_id else "❌", "联赛ID存在"))
        checks.append(("✅" if match.home_team_id and home_team else "⚠️", f"主队信息完整"))
        checks.append(("✅" if match.away_team_id and away_team else "⚠️", f"客队信息完整"))
        checks.append(("✅" if match.match_date else "❌", "比赛时间存在"))
        
        if match.status == "FINISHED":
            checks.append(("✅" if match.home_score is not None and match.away_score is not None else "❌", 
                          "已完成比赛有比分"))
            checks.append(("✅" if match.result else "⚠️", "已完成比赛有结果"))
        
        for status, desc in checks:
            print(f"  {status} {desc}")
        
        print("=" * 80)


async def inspect_data_sources():
    """检查数据来源分布"""
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("📌 数据来源统计")
        print("=" * 80)
        
        # 获取所有比赛
        stmt = select(Match)
        result = await db.execute(stmt)
        all_matches = result.scalars().all()
        
        # 统计来源
        api_data = [m for m in all_matches if m.tags and 'ImportedFromAPI' in m.tags]
        unknown_data = [m for m in all_matches if not m.tags or 'ImportedFromAPI' not in m.tags]
        
        total = len(all_matches)
        api_count = len(api_data)
        unknown_count = len(unknown_data)
        
        print(f"\n总比赛数:           {total:>6} 场")
        print(f"✅ 来自官方API:      {api_count:>6} 场 ({api_count/total*100:.1f}%)" if total > 0 else "N/A")
        print(f"❌ 来源未知:         {unknown_count:>6} 场 ({unknown_count/total*100:.1f}%)" if total > 0 else "N/A")
        
        if unknown_count > 0:
            print("\n⚠️  警告: 发现非API来源数据，请检查以下比赛:")
            print(f"\n{'比赛ID':<35} {'主队 vs 客队':<40} {'日期':<12}")
            print("-" * 90)
            for match in unknown_data[:10]:  # 只显示前10条
                teams = f"{match.home_team_id} vs {match.away_team_id}"
                date_str = match.match_date.strftime("%Y-%m-%d") if match.match_date else "N/A"
                print(f"{match.match_id:<35} {teams:<40} {date_str:<12}")
            
            if unknown_count > 10:
                print(f"\n... 还有 {unknown_count - 10} 场未显示")
        else:
            print("\n✅ 所有数据均来自官方API，数据可信！")
        
        print("=" * 80)


async def compare_with_expected():
    """与预期数据量对比"""
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("📊 数据完整性检查 - 与预期对比")
        print("=" * 80)
        
        # 预期的赛季数据量（参考值）
        expected_matches = {
            "EPL": 380,    # 英超：20支球队，38轮
            "BL1": 306,    # 德甲：18支球队，34轮
            "PD": 380,     # 西甲：20支球队，38轮
            "SA": 380,     # 意甲：20支球队，38轮
            "FL1": 306,    # 法甲：18支球队，34轮
        }
        
        print(f"\n{'联赛':<10} {'当前数据':<12} {'预期全赛季':<15} {'完成度':<10} {'评估'}")
        print("-" * 70)
        
        for league_id, expected in expected_matches.items():
            # 查询当前数据量
            stmt = select(func.count()).select_from(Match).where(
                Match.league_id == league_id
            )
            result = await db.execute(stmt)
            current = result.scalar()
            
            if current == 0:
                completion = "0%"
                assessment = "❌ 无数据"
            else:
                completion_rate = (current / expected) * 100
                completion = f"{completion_rate:.1f}%"
                
                if completion_rate >= 80:
                    assessment = "✅ 数据充足"
                elif completion_rate >= 50:
                    assessment = "⚠️  数据较少"
                else:
                    assessment = "❌ 数据不足"
            
            print(f"{league_id:<10} {current:<12} {expected:<15} {completion:<10} {assessment}")
        
        print("\n💡 提示:")
        print("   - 如果是赛季中期，数据量低于预期是正常的")
        print("   - 如果数据量为0或很少，建议重新运行数据摄取")
        print("   - 命令: python src/data_pipeline/ingest_football_data_v2.py")
        print("=" * 80)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据检查工具")
    parser.add_argument("--recent", action="store_true", help="查看最近的比赛")
    parser.add_argument("--leagues", action="store_true", help="按联赛统计")
    parser.add_argument("--match", type=str, help="查看特定比赛详情（提供match_id）")
    parser.add_argument("--sources", action="store_true", help="检查数据来源")
    parser.add_argument("--expected", action="store_true", help="与预期数据对比")
    parser.add_argument("--all", action="store_true", help="显示所有检查")
    
    args = parser.parse_args()
    
    # 如果没有参数，显示所有
    if not any([args.recent, args.leagues, args.match, args.sources, args.expected, args.all]):
        args.all = True
    
    print("\n🔍 正在检查数据库...")
    
    if args.all or args.sources:
        await inspect_data_sources()
    
    if args.all or args.leagues:
        await inspect_data_by_league()
    
    if args.all or args.expected:
        await compare_with_expected()
    
    if args.all or args.recent:
        await inspect_recent_matches()
    
    if args.match:
        await inspect_specific_match(args.match)
    
    print("\n✅ 数据检查完成！")
    print("\n💡 如果发现数据问题，可以:")
    print("   1. 重新运行数据摄取: python src/data_pipeline/ingest_football_data_v2.py")
    print("   2. 检查API密钥配置: config/service.yaml")
    print("   3. 查看完整文档: docs/DATA_INGESTION_FAQ.md")


if __name__ == "__main__":
    asyncio.run(main())

