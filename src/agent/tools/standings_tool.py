"""
StandingsTool - 积分榜查询工具
"""
from sqlalchemy.future import select
from sqlalchemy import and_
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Standing, Team
from src.data_pipeline.entity_resolver import entity_resolver
import logging

logger = logging.getLogger(__name__)


class StandingsTool:
    """
    积分榜查询工具
    
    功能：
    1. 查询联赛积分榜（完整榜单或 Top N）
    2. 查询特定球队的排名和积分
    """
    
    async def get_league_standings(
        self, 
        league_name: str = "英超", 
        season: str = "2024",
        top_n: int = 20
    ) -> str:
        """
        获取联赛积分榜
        
        Args:
            league_name: 联赛名称（中文或英文）
            season: 赛季（如 "2024"）
            top_n: 返回前 N 名球队，默认 20
            
        Returns:
            格式化的积分榜文本
        """
        try:
            # 联赛名称映射
            league_id_map = {
                "英超": "EPL",
                "英格兰超级联赛": "EPL",
                "EPL": "EPL",
                "Premier League": "EPL",
                "德甲": "BL1",
                "西甲": "PD",
                "意甲": "SA",
                "法甲": "FL1",
                "欧冠": "UCL",
            }
            
            league_id = league_id_map.get(league_name)
            if not league_id:
                return f"系统提示：未识别的联赛名称 \"{league_name}\"。支持的联赛：英超、德甲、西甲、意甲、法甲、欧冠。"
            
            # 查询积分榜
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Standing, Team)
                    .join(Team, Standing.team_id == Team.team_id)
                    .where(
                        and_(
                            Standing.league_id == league_id,
                            Standing.season == season
                        )
                    )
                    .order_by(Standing.position.asc())
                    .limit(top_n)
                )
                
                result = await session.execute(stmt)
                standings_with_teams = result.all()
            
            if not standings_with_teams:
                return f"数据库中暂无 {league_name} {season} 赛季的积分榜数据。"
            
            # 格式化输出
            lines = [f"【{league_name} {season} 赛季积分榜】"]
            lines.append("=" * 80)
            lines.append(f"{'排名':<4} {'球队':<25} {'场次':<4} {'胜':<3} {'平':<3} {'负':<3} {'进球':<4} {'失球':<4} {'净胜球':<6} {'积分':<4}")
            lines.append("-" * 80)
            
            for standing, team in standings_with_teams:
                line = (
                    f"{standing.position:<4} "
                    f"{team.team_name:<25} "
                    f"{standing.played_games:<4} "
                    f"{standing.won:<3} "
                    f"{standing.draw:<3} "
                    f"{standing.lost:<3} "
                    f"{standing.goals_for:<4} "
                    f"{standing.goals_against:<4} "
                    f"{standing.goal_difference:+6} "
                    f"{standing.points:<4}"
                )
                lines.append(line)
            
            lines.append("=" * 80)
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"查询积分榜失败: {e}")
            return f"系统错误：查询积分榜失败 ({str(e)})"
    
    async def get_team_standing(
        self, 
        team_name: str,
        season: str = "2024"
    ) -> str:
        """
        获取特定球队的积分榜信息
        
        Args:
            team_name: 球队名称
            season: 赛季
            
        Returns:
            格式化的球队积分榜信息
        """
        try:
            # 实体对齐
            team_id = await entity_resolver.resolve_team(team_name, source="user_query")
            if not team_id:
                return f"系统提示：未在数据库中找到名为 \"{team_name}\" 的球队。"
            
            # 查询球队积分榜信息
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Standing, Team)
                    .join(Team, Standing.team_id == Team.team_id)
                    .where(
                        and_(
                            Standing.team_id == team_id,
                            Standing.season == season
                        )
                    )
                )
                
                result = await session.execute(stmt)
                standing_with_team = result.first()
            
            if not standing_with_team:
                return f"数据库中暂无 {team_name} 在 {season} 赛季的积分榜数据。"
            
            standing, team = standing_with_team
            
            # 格式化输出
            lines = [f"【{team.team_name} - {season} 赛季积分榜信息】"]
            lines.append("=" * 60)
            lines.append(f"排名: 第 {standing.position} 位")
            lines.append(f"积分: {standing.points} 分")
            lines.append(f"比赛场次: {standing.played_games} 场")
            lines.append(f"战绩: {standing.won} 胜 {standing.draw} 平 {standing.lost} 负")
            lines.append(f"进球: {standing.goals_for} 个")
            lines.append(f"失球: {standing.goals_against} 个")
            lines.append(f"净胜球: {standing.goal_difference:+d}")
            lines.append("=" * 60)
            
            # 添加简要分析
            if standing.position <= 4:
                lines.append(f"分析: {team.team_name} 目前排名前四，有望获得欧冠资格。")
            elif standing.position <= 7:
                lines.append(f"分析: {team.team_name} 处于欧战区边缘，需要继续争取积分。")
            elif standing.position >= 18:
                lines.append(f"分析: {team.team_name} 目前处于降级区，形势严峻。")
            else:
                lines.append(f"分析: {team.team_name} 目前处于中游位置。")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"查询球队积分榜信息失败: {e}")
            return f"系统错误：查询失败 ({str(e)})"


# 单例导出
standings_tool = StandingsTool()

