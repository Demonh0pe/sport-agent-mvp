#!/usr/bin/env python3
"""
数据库状态查询工具
用法: python scripts/check_database_status.py [选项]

选项:
  --table <表名>  查看指定表的详细信息
  --teams         查看所有球队
  --leagues       查看所有联赛
  --matches       查看最近的比赛
  --standings     查看积分榜
  --summary       查看数据摘要（默认）
  --all           查看所有详细信息
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到路径
sys.path.insert(0, ".")

from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import League, Team, Match, Standing


async def check_database_connection():
    """检查数据库连接"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT version()"))
            version = result.scalar()
            print("[OK] 数据库连接成功")
            print(f"[INFO] PostgreSQL版本: {version.split(',')[0]}\n")
            return True
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        return False


async def get_table_counts(db: AsyncSession):
    """获取各表的记录数"""
    print("=" * 80)
    print("[统计] 数据库表统计")
    print("=" * 80)
    
    tables = {
        "联赛 (leagues)": League,
        "球队 (teams)": Team,
        "比赛 (matches)": Match,
        "积分榜 (standings)": Standing,
    }
    
    for name, model in tables.items():
        stmt = select(func.count()).select_from(model)
        result = await db.execute(stmt)
        count = result.scalar()
        print(f"  {name:30} {count:>10,} 条记录")
    
    print("=" * 80)
    print()


async def show_leagues(db: AsyncSession):
    """显示所有联赛"""
    print("=" * 80)
    print("联赛列表")
    print("=" * 80)
    
    stmt = select(League).order_by(League.league_name)
    result = await db.execute(stmt)
    leagues = result.scalars().all()
    
    if not leagues:
        print("  [WARN] 未找到联赛数据")
    else:
        for league in leagues:
            print(f"\n  [*] {league.league_name}")
            print(f"     ID: {league.league_id}")
            print(f"     国家: {league.country}")
            print(f"     级别: {league.level}")
    
    print("=" * 80)
    print()


async def show_teams(db: AsyncSession, league_id: Optional[str] = None):
    """显示球队列表"""
    print("=" * 80)
    print("球队列表")
    print("=" * 80)
    
    stmt = select(Team)
    if league_id:
        stmt = stmt.where(Team.league_id == league_id)
    stmt = stmt.order_by(Team.league_id, Team.team_name)
    
    result = await db.execute(stmt)
    teams = result.scalars().all()
    
    if not teams:
        print("  [WARN] 未找到球队数据")
    else:
        current_league = None
        for team in teams:
            if team.league_id != current_league:
                current_league = team.league_id
                print(f"\n  [{current_league}]")
            print(f"    - {team.team_name} ({team.team_id})")
    
    print(f"\n  总计: {len(teams)} 支球队")
    print("=" * 80)
    print()


async def show_recent_matches(db: AsyncSession, limit: int = 20):
    """显示最近的比赛"""
    print("=" * 80)
    print(f"最近 {limit} 场比赛")
    print("=" * 80)
    
    stmt = (
        select(Match)
        .order_by(Match.match_date.desc())
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    matches = result.scalars().all()
    
    if not matches:
        print("  [WARN] 未找到比赛数据")
    else:
        print(f"\n  {'日期':<12} {'主队':<20} {'比分':<10} {'客队':<20} {'状态':<10}")
        print("  " + "-" * 80)
        
        for match in matches:
            date_str = match.match_date.strftime("%Y-%m-%d") if match.match_date else "N/A"
            score = f"{match.home_score or '-'}:{match.away_score or '-'}"
            status_mark = "[OK]" if match.status == "FINISHED" else "[PENDING]"
            
            # 获取球队名称
            home_name = match.home_team_id
            away_name = match.away_team_id
            
            print(f"  {date_str:<12} {home_name:<20} {score:^10} {away_name:<20} {status_mark} {match.status:<10}")
    
    print("=" * 80)
    print()


async def show_standings(db: AsyncSession, league_id: Optional[str] = None, limit: int = 10):
    """显示积分榜"""
    print("=" * 80)
    print("积分榜")
    print("=" * 80)
    
    stmt = select(Standing, Team.team_name).join(Team, Standing.team_id == Team.team_id)
    
    if league_id:
        stmt = stmt.where(Standing.league_id == league_id)
    
    stmt = stmt.order_by(Standing.league_id, Standing.position).limit(limit)
    
    result = await db.execute(stmt)
    standings = result.all()
    
    if not standings:
        print("  [WARN] 未找到积分榜数据")
    else:
        current_league = None
        print(f"\n  {'排名':<6} {'球队':<25} {'赛':<4} {'胜':<4} {'平':<4} {'负':<4} {'进':<5} {'失':<5} {'净胜':<6} {'积分':<6}")
        print("  " + "-" * 80)
        
        for standing, team_name in standings:
            if standing.league_id != current_league:
                current_league = standing.league_id
                print(f"\n  [{current_league}]")
            
            print(f"  {standing.position:<6} {team_name:<25} {standing.played_games:<4} {standing.won:<4} "
                  f"{standing.draw:<4} {standing.lost:<4} {standing.goals_for:<5} {standing.goals_against:<5} "
                  f"{standing.goal_difference:>+6} {standing.points:<6}")
    
    print("=" * 80)
    print()


async def show_match_statistics(db: AsyncSession):
    """显示比赛统计信息"""
    print("=" * 80)
    print("比赛统计")
    print("=" * 80)
    
    # 按状态统计
    stmt = select(Match.status, func.count()).group_by(Match.status)
    result = await db.execute(stmt)
    status_counts = dict(result.all())
    
    print("\n  比赛状态分布:")
    for status, count in status_counts.items():
        mark = "[OK]" if status == "FINISHED" else "[PENDING]" if status == "SCHEDULED" else "[ACTIVE]"
        print(f"    {mark} {status:<15} {count:>6,} 场")
    
    # 按联赛统计
    stmt = select(Match.league_id, func.count()).group_by(Match.league_id)
    result = await db.execute(stmt)
    league_counts = dict(result.all())
    
    print("\n  联赛比赛数量:")
    for league_id, count in league_counts.items():
        print(f"    [*] {league_id:<15} {count:>6,} 场")
    
    # 时间范围
    stmt = select(
        func.min(Match.match_date),
        func.max(Match.match_date)
    )
    result = await db.execute(stmt)
    min_date, max_date = result.one()
    
    if min_date and max_date:
        print(f"\n  比赛时间范围:")
        print(f"    最早: {min_date.strftime('%Y-%m-%d')}")
        print(f"    最晚: {max_date.strftime('%Y-%m-%d')}")
    
    print("=" * 80)
    print()


async def show_data_quality(db: AsyncSession):
    """显示数据质量信息"""
    print("=" * 80)
    print("数据质量检查")
    print("=" * 80)
    
    # 检查没有比赛的球队
    stmt = select(func.count(Team.team_id)).where(
        ~Team.team_id.in_(
            select(Match.home_team_id).union(select(Match.away_team_id))
        )
    )
    result = await db.execute(stmt)
    teams_without_matches = result.scalar()
    
    print(f"\n  [WARN] 没有比赛记录的球队: {teams_without_matches}")
    
    # 检查完成但没有比分的比赛
    stmt = select(func.count()).where(
        Match.status == "FINISHED",
        (Match.home_score.is_(None)) | (Match.away_score.is_(None))
    )
    result = await db.execute(stmt)
    finished_without_score = result.scalar()
    
    print(f"  [WARN] 已完成但缺少比分的比赛: {finished_without_score}")
    
    # 检查积分榜覆盖
    stmt = select(func.count(func.distinct(Standing.league_id)))
    result = await db.execute(stmt)
    leagues_with_standings = result.scalar()
    
    stmt = select(func.count(func.distinct(League.league_id)))
    result = await db.execute(stmt)
    total_leagues = result.scalar()
    
    print(f"  [OK] 有积分榜的联赛: {leagues_with_standings}/{total_leagues}")
    
    print("=" * 80)
    print()


async def show_specific_table(db: AsyncSession, table_name: str):
    """显示指定表的详细信息"""
    table_mapping = {
        "leagues": (League, "联赛"),
        "teams": (Team, "球队"),
        "matches": (Match, "比赛"),
        "standings": (Standing, "积分榜"),
    }
    
    if table_name not in table_mapping:
        print(f"[ERROR] 未知表名: {table_name}")
        print(f"   可用的表: {', '.join(table_mapping.keys())}")
        return
    
    model, cn_name = table_mapping[table_name]
    
    print("=" * 80)
    print(f"📋 {cn_name}表 ({table_name}) 详细信息")
    print("=" * 80)
    
    # 记录数
    stmt = select(func.count()).select_from(model)
    result = await db.execute(stmt)
    count = result.scalar()
    print(f"\n  总记录数: {count:,}")
    
    # 示例数据
    stmt = select(model).limit(5)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    if records:
        print(f"\n  示例数据（前5条）:")
        for i, record in enumerate(records, 1):
            print(f"\n  [{i}]")
            for key, value in record.__dict__.items():
                if not key.startswith('_'):
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"    {key}: {value}")
    
    print("=" * 80)
    print()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库状态查询工具")
    parser.add_argument("--table", help="查看指定表的详细信息")
    parser.add_argument("--teams", action="store_true", help="查看所有球队")
    parser.add_argument("--leagues", action="store_true", help="查看所有联赛")
    parser.add_argument("--matches", action="store_true", help="查看最近的比赛")
    parser.add_argument("--standings", action="store_true", help="查看积分榜")
    parser.add_argument("--summary", action="store_true", help="查看数据摘要（默认）")
    parser.add_argument("--all", action="store_true", help="查看所有详细信息")
    parser.add_argument("--league", help="指定联赛ID过滤")
    parser.add_argument("--limit", type=int, default=20, help="限制显示数量")
    
    args = parser.parse_args()
    
    # 检查数据库连接
    if not await check_database_connection():
        return
    
    async with AsyncSessionLocal() as db:
        # 默认显示摘要
        if not any([args.table, args.teams, args.leagues, args.matches, 
                   args.standings, args.all]):
            args.summary = True
        
        # 显示摘要
        if args.summary or args.all:
            await get_table_counts(db)
            await show_match_statistics(db)
            await show_data_quality(db)
        
        # 显示联赛
        if args.leagues or args.all:
            await show_leagues(db)
        
        # 显示球队
        if args.teams or args.all:
            await show_teams(db, args.league)
        
        # 显示比赛
        if args.matches or args.all:
            await show_recent_matches(db, args.limit)
        
        # 显示积分榜
        if args.standings or args.all:
            await show_standings(db, args.league, args.limit)
        
        # 显示指定表
        if args.table:
            await show_specific_table(db, args.table)
    
    print("\n[OK] 查询完成！")


if __name__ == "__main__":
    asyncio.run(main())

