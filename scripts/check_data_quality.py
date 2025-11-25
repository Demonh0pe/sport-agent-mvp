"""
检查数据质量
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy import select, func
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match, Standing, Team, League


async def main():
    print("=" * 80)
    print("数据质量检查")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # 1. 比赛数据统计
        total_matches = (await db.execute(select(func.count(Match.match_id)))).scalar_one()
        finished_matches = (await db.execute(
            select(func.count(Match.match_id)).where(Match.status == "FINISHED")
        )).scalar_one()
        
        print(f"\n比赛数据:")
        print(f"  总比赛数: {total_matches}")
        print(f"  已完成: {finished_matches}")
        print(f"  未完成: {total_matches - finished_matches}")
        
        # 2. 积分榜数据统计
        total_standings = (await db.execute(select(func.count(Standing.id)))).scalar_one()
        
        print(f"\n积分榜数据:")
        print(f"  总记录数: {total_standings}")
        
        # 按联赛统计
        result = await db.execute(
            select(Standing.league_id, func.count(Standing.id))
            .group_by(Standing.league_id)
            .order_by(Standing.league_id)
        )
        print(f"\n  按联赛分布:")
        for league_id, count in result.all():
            print(f"    {league_id}: {count} 条")
        
        # 3. 检查是否有球队缺少积分榜数据
        teams_count = (await db.execute(select(func.count(Team.team_id)))).scalar_one()
        print(f"\n球队数据:")
        print(f"  总球队数: {teams_count}")
        
        # 检查有多少球队有积分榜数据
        result = await db.execute(
            select(func.count(func.distinct(Standing.team_id)))
        )
        teams_with_standings = result.scalar_one()
        print(f"  有积分榜的球队: {teams_with_standings}")
        print(f"  缺少积分榜的球队: {teams_count - teams_with_standings}")
        
        # 4. 检查2024赛季的积分榜
        result = await db.execute(
            select(func.count(Standing.id)).where(Standing.season == "2024")
        )
        standings_2024 = result.scalar_one()
        print(f"\n2024赛季积分榜: {standings_2024} 条")
        
        # 5. 检查有result的比赛
        result = await db.execute(
            select(func.count(Match.match_id)).where(Match.result.isnot(None))
        )
        matches_with_result = result.scalar_one()
        print(f"\n有结果的比赛: {matches_with_result}/{finished_matches}")
        
        # 6. 抽样检查几场比赛
        print("\n" + "=" * 80)
        print("抽样检查比赛和积分榜")
        print("=" * 80)
        
        # 随机选择一场比赛
        result = await db.execute(
            select(Match)
            .where(Match.status == "FINISHED")
            .where(Match.result.isnot(None))
            .limit(1)
        )
        match = result.scalar_one_or_none()
        
        if match:
            print(f"\n比赛: {match.home_team_id} vs {match.away_team_id}")
            print(f"联赛: {match.league_id}")
            print(f"结果: {match.result}")
            
            # 检查这两个球队的积分榜
            for team_id in [match.home_team_id, match.away_team_id]:
                result = await db.execute(
                    select(Standing).where(
                        Standing.team_id == team_id,
                        Standing.league_id == match.league_id,
                        Standing.season == "2024"
                    )
                )
                standing = result.scalar_one_or_none()
                
                if standing:
                    print(f"\n{team_id} 积分榜:")
                    print(f"  排名: {standing.position}")
                    print(f"  积分: {standing.points}")
                    print(f"  进球: {standing.goals_for}")
                    print(f"  失球: {standing.goals_against}")
                else:
                    print(f"\n{team_id}: 无积分榜数据!")
        
        print("\n" + "=" * 80)
        print("检查完成")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

