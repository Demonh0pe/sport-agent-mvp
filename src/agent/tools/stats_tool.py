"""
Stats Tool: 球队统计分析工具

功能：
1. 球队近期战绩分析
2. 进攻/防守效率统计
3. 主客场表现对比
4. 连胜/连败趋势
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.future import select as async_select
from datetime import datetime, timedelta, timezone

from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Match, Team

logger = logging.getLogger(__name__)


class StatsTool:
    """球队统计分析工具"""
    
    async def get_team_stats(
        self, 
        team_name: str,
        last_n: int = 10,
        venue: Optional[str] = None  # "home", "away", or None (all)
    ) -> str:
        """
        获取球队统计数据
        
        Args:
            team_name: 球队名称（可以是中英文）
            last_n: 分析最近N场比赛
            venue: 场地限制（home/away/None）
            
        Returns:
            格式化的统计报告文本
        """
        try:
            # 1. 球队实体对齐
            team_id = await self._lookup_team(team_name)
            if not team_id:
                return f"系统提示：未找到球队\"{team_name}\"。"
            
            # 2. 获取比赛数据
            matches = await self._fetch_matches(team_id, last_n, venue)
            
            if not matches:
                venue_desc = {"home": "主场", "away": "客场"}.get(venue, "")
                return f"数据库中暂无 {team_name} 的{venue_desc}比赛记录。"
            
            # 3. 计算统计指标
            stats = self._calculate_stats(matches, team_id)
            
            # 4. 格式化输出
            report = self._format_stats_report(
                team_name=team_name,
                team_id=team_id,
                stats=stats,
                venue=venue
            )
            
            return report
            
        except Exception as e:
            logger.error(f"StatsTool error: {e}", exc_info=True)
            return f"系统错误：统计数据获取失败 ({str(e)})"
    
    async def _lookup_team(self, team_name: str) -> Optional[str]:
        """查询球队ID"""
        async with AsyncSessionLocal() as db:
            # 模糊匹配球队名称
            stmt = select(Team).where(
                or_(
                    Team.team_name.ilike(f"%{team_name}%"),
                    Team.team_id.ilike(f"%{team_name}%")
                )
            )
            result = await db.execute(stmt)
            team = result.scalars().first()
            
            return team.team_id if team else None
    
    async def _fetch_matches(
        self,
        team_id: str,
        last_n: int,
        venue: Optional[str]
    ) -> list:
        """获取比赛数据"""
        async with AsyncSessionLocal() as db:
            # 构建查询条件
            conditions = [
                Match.status == "FINISHED",  # 只统计已完成的比赛
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id
                )
            ]
            
            # 场地限制
            if venue == "home":
                conditions.append(Match.home_team_id == team_id)
            elif venue == "away":
                conditions.append(Match.away_team_id == team_id)
            
            # 执行查询
            stmt = select(Match).where(
                and_(*conditions)
            ).order_by(Match.match_date.desc()).limit(last_n)
            
            result = await db.execute(stmt)
            return result.scalars().all()
    
    def _calculate_stats(self, matches: list, team_id: str) -> Dict[str, Any]:
        """计算统计指标"""
        stats = {
            "total_matches": len(matches),
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "clean_sheets": 0,  # 零封场次
            "failed_to_score": 0,  # 未进球场次
            "streak": {  # 连胜/连败
                "type": None,  # "win", "draw", "loss"
                "count": 0
            },
            "recent_form": []  # 最近5场：W/D/L
        }
        
        for match in matches:
            # 判断主客场
            is_home = (match.home_team_id == team_id)
            
            # 获取比分
            if is_home:
                scored = match.home_score or 0
                conceded = match.away_score or 0
            else:
                scored = match.away_score or 0
                conceded = match.home_score or 0
            
            stats["goals_scored"] += scored
            stats["goals_conceded"] += conceded
            
            # 判断比赛结果
            if scored > conceded:
                result = "W"
                stats["wins"] += 1
            elif scored == conceded:
                result = "D"
                stats["draws"] += 1
            else:
                result = "L"
                stats["losses"] += 1
            
            # 记录最近5场形态
            if len(stats["recent_form"]) < 5:
                stats["recent_form"].append(result)
            
            # 零封统计
            if conceded == 0:
                stats["clean_sheets"] += 1
            
            # 未进球统计
            if scored == 0:
                stats["failed_to_score"] += 1
        
        # 计算派生指标
        if stats["total_matches"] > 0:
            stats["win_rate"] = stats["wins"] / stats["total_matches"] * 100
            stats["avg_goals_scored"] = stats["goals_scored"] / stats["total_matches"]
            stats["avg_goals_conceded"] = stats["goals_conceded"] / stats["total_matches"]
            stats["goal_difference"] = stats["goals_scored"] - stats["goals_conceded"]
        
        # 分析连胜/连败趋势
        stats["streak"] = self._analyze_streak(stats["recent_form"])
        
        return stats
    
    def _analyze_streak(self, form: list) -> Dict[str, Any]:
        """分析连胜/连败"""
        if not form:
            return {"type": None, "count": 0}
        
        current = form[0]
        count = 1
        
        for result in form[1:]:
            if result == current:
                count += 1
            else:
                break
        
        return {
            "type": {"W": "连胜", "D": "连平", "L": "连败"}.get(current, ""),
            "count": count
        }
    
    def _format_stats_report(
        self,
        team_name: str,
        team_id: str,
        stats: Dict[str, Any],
        venue: Optional[str]
    ) -> str:
        """格式化统计报告"""
        venue_desc = {
            "home": "主场",
            "away": "客场",
            None: ""
        }.get(venue, "")
        
        report_lines = [
            f"📊 {team_name} ({team_id}) {venue_desc}统计分析",
            f"═" * 50,
            f"",
            f"📈 基础数据（最近 {stats['total_matches']} 场）：",
            f"  - 胜/平/负：{stats['wins']} / {stats['draws']} / {stats['losses']}",
            f"  - 胜率：{stats.get('win_rate', 0):.1f}%",
            f"  - 总进球：{stats['goals_scored']} 球（场均 {stats.get('avg_goals_scored', 0):.2f}）",
            f"  - 总失球：{stats['goals_conceded']} 球（场均 {stats.get('avg_goals_conceded', 0):.2f}）",
            f"  - 净胜球：{stats.get('goal_difference', 0):+d}",
            f"",
            f"🛡️ 防守数据：",
            f"  - 零封场次：{stats['clean_sheets']} 场",
            f"  - 零封率：{stats['clean_sheets'] / stats['total_matches'] * 100:.1f}%",
            f"",
            f"⚽ 进攻数据：",
            f"  - 未进球场次：{stats['failed_to_score']} 场",
            f"  - 破门率：{(stats['total_matches'] - stats['failed_to_score']) / stats['total_matches'] * 100:.1f}%",
            f"",
            f"🔥 近期状态：",
            f"  - 最近5场：{' '.join(stats['recent_form'])}",
        ]
        
        # 添加连胜/连败信息
        streak = stats['streak']
        if streak['count'] >= 2:
            report_lines.append(f"  - 当前：{streak['type']} {streak['count']} 场")
        
        return "\n".join(report_lines)


# 全局单例
stats_tool = StatsTool()

