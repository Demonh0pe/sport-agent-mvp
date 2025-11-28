"""Match Tool: Agent 访问赛事数据的'手' (真实数据库版)。"""
import logging
from typing import Optional
from sqlalchemy import or_, and_, func
from sqlalchemy.future import select
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Team, Match

logger = logging.getLogger(__name__)

class MatchTool:
    async def lookup_team_id(self, query_name: str) -> Optional[str]:
        """
        【实体消歧】
        将用户的口语（如'曼联'）映射为数据库的标准ID（'MUN'）。
        """
        try:
            async with AsyncSessionLocal() as session:
                # 模糊匹配：名字包含 query_name
                stmt = select(Team).where(
                    or_(
                        Team.team_name.ilike(f"%{query_name}%"),
                        Team.team_id.ilike(f"{query_name}")
                    )
                )
                result = await session.execute(stmt)
                team = result.scalars().first()
                
                return team.team_id if team else None
        except Exception as e:
            logger.error(f"Lookup failed for {query_name}: {e}")
            return None

    async def get_recent_matches(self, team_name: str, limit: int = 5) -> str:
        """
        【上下文获取】
        查询比赛数据，并将其序列化为 LLM 易读的文本格式。
        """
        try:
            # 1. 先把名字对齐
            team_id = await self.lookup_team_id(team_name)
            if not team_id:
                return f"系统提示：未在数据库中找到名为“{team_name}”的球队。（可能是数据库暂无数据，或名称拼写错误）"

            # 2. 查库 - 优先返回已完成的比赛，不足时补充未来的比赛
            # [重要] 只返回来自API的真实数据，过滤掉Seed/Mock数据
            async with AsyncSessionLocal() as session:
                # 先查询已完成的比赛（按日期降序）
                # 为了避免SQL兼容性问题，我们查询更多数据，然后在Python层面过滤
                finished_stmt = select(Match).where(
                    and_(
                        or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                        Match.status == "FINISHED"
                    )
                ).order_by(Match.match_date.desc()).limit(limit * 3)  # 查询3倍数据以确保过滤后足够
                
                result = await session.execute(finished_stmt)
                all_finished = list(result.scalars().all())
                
                # [过滤] 在Python层面过滤：只保留包含'ImportedFromAPI'标签的真实数据
                matches = [
                    m for m in all_finished 
                    if m.tags and 'ImportedFromAPI' in m.tags
                ][:limit]  # 只取前limit条
                
                # 如果已完成比赛数量不足，补充未来的比赛
                if len(matches) < limit:
                    fixture_stmt = select(Match).where(
                        and_(
                            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                            Match.status == "FIXTURE"
                        )
                    ).order_by(Match.match_date.asc()).limit((limit - len(matches)) * 3)
                    
                    result = await session.execute(fixture_stmt)
                    all_fixtures = list(result.scalars().all())
                    
                    # [过滤] 同样在Python层面过滤
                    filtered_fixtures = [
                        m for m in all_fixtures
                        if m.tags and 'ImportedFromAPI' in m.tags
                    ][:limit - len(matches)]  # 只取需要的数量
                    
                    matches.extend(filtered_fixtures)

            if not matches:
                return f"数据库中暂无 {team_name} 的近期比赛记录。"

            # 3. 数据转文本
            lines = [f"[统计] {team_name} ({team_id}) 近 {limit} 场比赛记录："]
            
            for m in matches:
                score_str = f"{m.home_score} : {m.away_score}" if m.status == "FINISHED" else "未开赛"
                
                result_desc = ""
                if m.status == "FINISHED":
                    if m.result == 'H' and m.home_team_id == team_id: result_desc = "(胜)"
                    elif m.result == 'A' and m.away_team_id == team_id: result_desc = "(胜)"
                    elif m.result == 'D': result_desc = "(平)"
                    else: result_desc = "(负)"

                line = f"- 日期: {m.match_date.strftime('%Y-%m-%d')} | 对阵: {m.home_team_id} vs {m.away_team_id} | 比分: {score_str} {result_desc}"
                lines.append(line)
                
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Get matches failed: {e}")
            return f"系统错误：查询比赛数据失败 ({str(e)})"

    async def get_head_to_head_matches(self, team_a_name: str, team_b_name: str, limit: int = 5):
        """
        【历史交锋】
        查询两支球队的历史交锋记录
        """
        try:
            # 1. 解析球队ID
            team_a_id = await self.lookup_team_id(team_a_name)
            team_b_id = await self.lookup_team_id(team_b_name)
            
            if not team_a_id or not team_b_id:
                return []
            
            # 2. 查询交锋记录
            async with AsyncSessionLocal() as session:
                stmt = select(Match).where(
                    and_(
                        or_(
                            and_(Match.home_team_id == team_a_id, Match.away_team_id == team_b_id),
                            and_(Match.home_team_id == team_b_id, Match.away_team_id == team_a_id)
                        ),
                        Match.status == "FINISHED"
                    )
                ).order_by(Match.match_date.desc()).limit(limit * 3)
                
                result = await session.execute(stmt)
                all_matches = list(result.scalars().all())
                
                # 过滤真实数据
                matches = [
                    m for m in all_matches 
                    if m.tags and 'ImportedFromAPI' in m.tags
                ][:limit]
                
                return matches
                
        except Exception as e:
            logger.error(f"Get H2H failed: {e}")
            return []

# 单例导出
match_tool = MatchTool()