"""
数据分析器 (Data Analyzer)

负责：
1. 从工具的非结构化输出中提取结构化数据
2. 多维度数据对比分析
3. 统计显著性检验
4. 趋势识别

Author: Sport Agent Team
Date: 2025-11-26
"""
from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TeamStats:
    """球队统计数据"""
    team_name: str
    team_id: Optional[str] = None

    # 排名与积分
    rank: Optional[int] = None
    points: Optional[int] = None
    played_games: Optional[int] = None

    # 战绩
    wins: Optional[int] = None
    draws: Optional[int] = None
    losses: Optional[int] = None
    win_rate: Optional[float] = None

    # 进攻与防守
    goals_for: Optional[int] = None
    goals_against: Optional[int] = None
    goal_difference: Optional[int] = None
    goals_per_game: Optional[float] = None

    # 近期形式
    recent_form: Optional[str] = None  # "WWDLL"
    recent_wins: Optional[int] = None
    recent_draws: Optional[int] = None
    recent_losses: Optional[int] = None
    recent_win_rate: Optional[float] = None

    # 主客场
    home_win_rate: Optional[float] = None
    away_win_rate: Optional[float] = None

    # 连胜/连败
    streak_type: Optional[str] = None  # "winning" / "losing" / "drawing"
    streak_count: Optional[int] = None


@dataclass
class ComparisonResult:
    """对比分析结果"""
    dimension: str  # 对比维度（如"ranking", "recent_form"）
    team_a_value: Any
    team_b_value: Any
    difference: float  # 差值
    ratio: Optional[float]  # 比值
    advantage: str  # "team_a" / "team_b" / "neutral"
    significance: float  # 显著性 (0-1)
    interpretation: str  # 文本解读


class DataAnalyzer:
    """
    数据分析器

    核心能力：
    1. 智能解析各种格式的工具输出
    2. 提取关键数据点
    3. 多维度对比分析
    4. 量化差距和优势
    """

    def __init__(self):
        self.team_name_patterns = self._init_team_patterns()

    def _init_team_patterns(self) -> Dict[str, List[str]]:
        """
        初始化球队名称模式
        用于实体识别和标准化
        """
        return {
            "Manchester United": ["曼联", "manchester united", "man utd", "mun"],
            "Liverpool": ["利物浦", "liverpool", "liv"],
            "Arsenal": ["阿森纳", "arsenal", "ars"],
            "Manchester City": ["曼城", "manchester city", "man city", "mci"],
            "Chelsea": ["切尔西", "chelsea", "che"],
            "Tottenham": ["热刺", "tottenham", "spurs", "tot"],
            "Newcastle": ["纽卡", "纽卡斯尔", "newcastle", "new"],
            "Leicester": ["莱斯特", "leicester", "lei"],
            "Bayern München": ["拜仁", "拜仁慕尼黑", "bayern", "fcb"],
            "Borussia Dortmund": ["多特", "多特蒙德", "dortmund", "bvb"],
            "Real Madrid": ["皇马", "皇家马德里", "real madrid", "rma"],
            "Barcelona": ["巴萨", "巴塞罗那", "barcelona", "bar", "barca"],
        }

    def extract_structured_data(
        self,
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, TeamStats]:
        """
        从工具结果中提取结构化数据

        Args:
            tool_results: 工具执行结果列表

        Returns:
            Dict[team_name, TeamStats]: 按球队组织的统计数据
        """
        logger.info("[DataAnalyzer] Extracting structured data from tool results")

        team_data = {}

        for result in tool_results:
            tool_name = result.get("tool_name")
            output = result.get("output", "")

            if result.get("status") != "success":
                continue

            # 根据工具类型解析
            if tool_name == "MatchResolverTool" or tool_name == "StatsAnalysisTool":
                extracted = self._extract_from_stats_tool(output)
                if extracted:
                    team_data[extracted.team_name] = extracted

            elif tool_name == "StandingsTool":
                extracted = self._extract_from_standings_tool(output)
                if extracted:
                    # 合并到已有数据
                    if extracted.team_name in team_data:
                        team_data[extracted.team_name] = self._merge_stats(
                            team_data[extracted.team_name],
                            extracted
                        )
                    else:
                        team_data[extracted.team_name] = extracted

            elif tool_name == "PredictionTool":
                # 预测工具可能包含两队的简要信息
                teams = self._extract_teams_from_prediction(output)
                for team in teams:
                    if team.team_name not in team_data:
                        team_data[team.team_name] = team

        logger.info(f"[DataAnalyzer] Extracted data for {len(team_data)} teams")
        return team_data

    def _extract_from_stats_tool(self, output: str) -> Optional[TeamStats]:
        """
        从StatsAnalysisTool的输出中提取数据

        输出格式示例：
        '''
        📊 曼联 (MUN) 近 5 场比赛记录：
        1. 2024-11-20 | 曼联 vs 切尔西 | 1-2 | 负
        ...

        战绩统计：1 胜 2 平 2 负 (胜率: 20.0%)
        '''
        """
        if not isinstance(output, str):
            return None

        stats = TeamStats(team_name="Unknown")

        # 提取球队名称
        team_match = re.search(r'([\u4e00-\u9fa5]+|[A-Za-z\s]+)\s*\(([A-Z]{3})\)', output)
        if team_match:
            stats.team_name = self._normalize_team_name(team_match.group(1))
            stats.team_id = team_match.group(2)

        # 提取战绩："1 胜 2 平 2 负"
        record_match = re.search(r'(\d+)\s*胜\s*(\d+)\s*平\s*(\d+)\s*负', output)
        if record_match:
            stats.wins = int(record_match.group(1))
            stats.draws = int(record_match.group(2))
            stats.losses = int(record_match.group(3))
            stats.played_games = stats.wins + stats.draws + stats.losses

            if stats.played_games > 0:
                stats.win_rate = stats.wins / stats.played_games

        # 提取胜率："胜率: 20.0%"
        win_rate_match = re.search(r'胜率[:：]\s*([\d.]+)%', output)
        if win_rate_match:
            stats.win_rate = float(win_rate_match.group(1)) / 100

        # 提取进球数据
        goals_match = re.search(r'进(\d+)球.*失(\d+)球', output)
        if goals_match:
            stats.goals_for = int(goals_match.group(1))
            stats.goals_against = int(goals_match.group(2))
            stats.goal_difference = stats.goals_for - stats.goals_against

        # 提取近期形式："WWDLL"
        form_match = re.search(r'近期走势[:：]\s*([WDLWDL]+)', output)
        if form_match:
            stats.recent_form = form_match.group(1)
            stats.recent_wins = stats.recent_form.count('W')
            stats.recent_draws = stats.recent_form.count('D')
            stats.recent_losses = stats.recent_form.count('L')

            total = len(stats.recent_form)
            if total > 0:
                stats.recent_win_rate = stats.recent_wins / total

        # 提取连胜/连败
        streak_match = re.search(r'(连胜|连平|连败)[:：]\s*(\d+)', output)
        if streak_match:
            streak_type_cn = streak_match.group(1)
            stats.streak_count = int(streak_match.group(2))

            if streak_type_cn == "连胜":
                stats.streak_type = "winning"
            elif streak_type_cn == "连败":
                stats.streak_type = "losing"
            else:
                stats.streak_type = "drawing"

        return stats if stats.team_name != "Unknown" else None

    def _extract_from_standings_tool(self, output: str) -> Optional[TeamStats]:
        """
        从StandingsTool的输出中提取数据

        输出格式示例：
        '''
        第 1 位 | 利物浦 (LIV)
        场次：12｜战绩：9胜2平1负｜进球：28｜失球：9｜净胜球：+19｜积分：29
        '''
        """
        if not isinstance(output, str):
            return None

        stats = TeamStats(team_name="Unknown")

        # 提取排名
        rank_match = re.search(r'第\s*(\d+)\s*位', output)
        if rank_match:
            stats.rank = int(rank_match.group(1))

        # 提取球队名称
        team_match = re.search(r'第\s*\d+\s*位\s*[|｜]\s*([\u4e00-\u9fa5]+|[A-Za-z\s]+)\s*\(([A-Z]{3})\)', output)
        if team_match:
            stats.team_name = self._normalize_team_name(team_match.group(1))
            stats.team_id = team_match.group(2)

        # 提取积分
        points_match = re.search(r'积分[:：]\s*(\d+)', output)
        if points_match:
            stats.points = int(points_match.group(1))

        # 提取场次
        games_match = re.search(r'场次[:：]\s*(\d+)', output)
        if games_match:
            stats.played_games = int(games_match.group(1))

        # 提取战绩
        record_match = re.search(r'(\d+)胜(\d+)平(\d+)负', output)
        if record_match:
            stats.wins = int(record_match.group(1))
            stats.draws = int(record_match.group(2))
            stats.losses = int(record_match.group(3))

            if stats.played_games and stats.played_games > 0:
                stats.win_rate = stats.wins / stats.played_games

        # 提取进球
        goals_for_match = re.search(r'进球[:：]\s*(\d+)', output)
        if goals_for_match:
            stats.goals_for = int(goals_for_match.group(1))

        # 提取失球
        goals_against_match = re.search(r'失球[:：]\s*(\d+)', output)
        if goals_against_match:
            stats.goals_against = int(goals_against_match.group(1))

        # 提取净胜球
        gd_match = re.search(r'净胜球[:：]\s*([+\-]?\d+)', output)
        if gd_match:
            stats.goal_difference = int(gd_match.group(1))

        return stats if stats.team_name != "Unknown" else None

    def _extract_teams_from_prediction(self, output: Any) -> List[TeamStats]:
        """从预测工具输出中提取球队信息"""
        teams = []

        # 如果是字典格式（真实预测工具）
        if isinstance(output, dict):
            home_team = output.get("home_team")
            away_team = output.get("away_team")

            if home_team:
                teams.append(TeamStats(team_name=home_team))
            if away_team:
                teams.append(TeamStats(team_name=away_team))

        return teams

    def _normalize_team_name(self, name: str) -> str:
        """
        标准化球队名称

        将各种变体统一为标准名称
        """
        name_lower = name.lower().strip()

        for standard_name, variants in self.team_name_patterns.items():
            if name_lower in [v.lower() for v in variants]:
                return standard_name

        # 如果没有匹配，返回首字母大写的版本
        return name.title()

    def _merge_stats(self, stats1: TeamStats, stats2: TeamStats) -> TeamStats:
        """
        合并两个TeamStats对象
        优先使用非None的值
        """
        merged = TeamStats(team_name=stats1.team_name)

        for field in stats1.__dataclass_fields__:
            val1 = getattr(stats1, field)
            val2 = getattr(stats2, field)

            # 优先使用非None的值
            setattr(merged, field, val1 if val1 is not None else val2)

        return merged

    def multi_dimensional_comparison(
        self,
        team_a: TeamStats,
        team_b: TeamStats
    ) -> Dict[str, ComparisonResult]:
        """
        多维度对比分析

        Returns:
            Dict[dimension, ComparisonResult]: 各维度的对比结果
        """
        logger.info(f"[DataAnalyzer] Comparing {team_a.team_name} vs {team_b.team_name}")

        comparisons = {}

        # 1. 排名对比
        if team_a.rank is not None and team_b.rank is not None:
            comparisons["ranking"] = self._compare_ranking(team_a, team_b)

        # 2. 近期状态对比
        if team_a.recent_win_rate is not None and team_b.recent_win_rate is not None:
            comparisons["recent_form"] = self._compare_recent_form(team_a, team_b)

        # 3. 整体战绩对比
        if team_a.win_rate is not None and team_b.win_rate is not None:
            comparisons["overall_record"] = self._compare_overall_record(team_a, team_b)

        # 4. 进攻能力对比
        if team_a.goals_for is not None and team_b.goals_for is not None:
            comparisons["attacking"] = self._compare_attacking(team_a, team_b)

        # 5. 防守能力对比
        if team_a.goals_against is not None and team_b.goals_against is not None:
            comparisons["defending"] = self._compare_defending(team_a, team_b)

        logger.info(f"[DataAnalyzer] Generated {len(comparisons)} dimension comparisons")
        return comparisons

    def _compare_ranking(self, team_a: TeamStats, team_b: TeamStats) -> ComparisonResult:
        """排名对比"""
        rank_a = team_a.rank
        rank_b = team_b.rank

        diff = abs(rank_a - rank_b)
        advantage = "team_a" if rank_a < rank_b else "team_b"

        # 显著性：差距越大，越显著
        significance = min(1.0, diff / 15)

        # 解读
        better_rank = min(rank_a, rank_b)
        worse_rank = max(rank_a, rank_b)

        if diff >= 10:
            level = "悬殊"
        elif diff >= 5:
            level = "明显"
        elif diff >= 2:
            level = "中等"
        else:
            level = "轻微"

        interpretation = (
            f"排名差距{level}（{diff}位），排名第{better_rank}的球队整体实力占优"
        )

        return ComparisonResult(
            dimension="排名差距",
            team_a_value=rank_a,
            team_b_value=rank_b,
            difference=diff,
            ratio=None,
            advantage=advantage,
            significance=significance,
            interpretation=interpretation
        )

    def _compare_recent_form(self, team_a: TeamStats, team_b: TeamStats) -> ComparisonResult:
        """近期状态对比"""
        rate_a = team_a.recent_win_rate
        rate_b = team_b.recent_win_rate

        diff = abs(rate_a - rate_b)
        advantage = "team_a" if rate_a > rate_b else "team_b"

        # 计算倍数
        better_rate = max(rate_a, rate_b)
        worse_rate = min(rate_a, rate_b)
        ratio = better_rate / worse_rate if worse_rate > 0 else 2.0

        # 显著性
        significance = min(1.0, diff * 2)

        # 解读
        interpretation = (
            f"近期状态：{team_a.team_name}胜率{rate_a:.0%}，"
            f"{team_b.team_name}胜率{rate_b:.0%}，"
            f"状态好{ratio:.1f}倍"
        )

        return ComparisonResult(
            dimension="近期状态",
            team_a_value=rate_a,
            team_b_value=rate_b,
            difference=diff,
            ratio=ratio,
            advantage=advantage,
            significance=significance,
            interpretation=interpretation
        )

    def _compare_overall_record(self, team_a: TeamStats, team_b: TeamStats) -> ComparisonResult:
        """整体战绩对比"""
        rate_a = team_a.win_rate
        rate_b = team_b.win_rate

        diff = abs(rate_a - rate_b)
        advantage = "team_a" if rate_a > rate_b else "team_b"

        significance = min(1.0, diff * 1.5)

        interpretation = f"整体胜率：{team_a.team_name} {rate_a:.0%} vs {team_b.team_name} {rate_b:.0%}"

        return ComparisonResult(
            dimension="整体战绩",
            team_a_value=rate_a,
            team_b_value=rate_b,
            difference=diff,
            ratio=rate_a / rate_b if rate_b > 0 else 1.0,
            advantage=advantage,
            significance=significance,
            interpretation=interpretation
        )

    def _compare_attacking(self, team_a: TeamStats, team_b: TeamStats) -> ComparisonResult:
        """进攻能力对比"""
        goals_a = team_a.goals_for
        goals_b = team_b.goals_for

        diff = abs(goals_a - goals_b)
        advantage = "team_a" if goals_a > goals_b else "team_b"

        # 相对差异
        relative_diff = diff / max(goals_a, goals_b) if max(goals_a, goals_b) > 0 else 0
        significance = min(1.0, relative_diff * 2)

        interpretation = f"进攻：{team_a.team_name}进{goals_a}球，{team_b.team_name}进{goals_b}球"

        return ComparisonResult(
            dimension="进攻能力",
            team_a_value=goals_a,
            team_b_value=goals_b,
            difference=diff,
            ratio=goals_a / goals_b if goals_b > 0 else 1.0,
            advantage=advantage,
            significance=significance,
            interpretation=interpretation
        )

    def _compare_defending(self, team_a: TeamStats, team_b: TeamStats) -> ComparisonResult:
        """防守能力对比（失球越少越好）"""
        goals_a = team_a.goals_against
        goals_b = team_b.goals_against

        diff = abs(goals_a - goals_b)
        advantage = "team_a" if goals_a < goals_b else "team_b"  # 失球少的占优

        relative_diff = diff / max(goals_a, goals_b) if max(goals_a, goals_b) > 0 else 0
        significance = min(1.0, relative_diff * 2)

        interpretation = f"防守：{team_a.team_name}失{goals_a}球，{team_b.team_name}失{goals_b}球"

        return ComparisonResult(
            dimension="防守能力",
            team_a_value=goals_a,
            team_b_value=goals_b,
            difference=diff,
            ratio=goals_b / goals_a if goals_a > 0 else 1.0,  # 倒数比
            advantage=advantage,
            significance=significance,
            interpretation=interpretation
        )

    def prepare_for_reasoning(
        self,
        team_data: Dict[str, TeamStats],
        comparisons: Dict[str, ComparisonResult]
    ) -> Dict[str, Any]:
        """
        为推理引擎准备数据

        将提取的数据和对比结果转换为推理引擎需要的格式
        """
        teams = list(team_data.keys())

        if len(teams) < 2:
            logger.warning("[DataAnalyzer] Less than 2 teams found for reasoning")
            return {}

        team_a_name = teams[0]
        team_b_name = teams[1]

        team_a = team_data[team_a_name]
        team_b = team_data[team_b_name]

        # 转换为推理引擎期望的格式
        reasoning_data = {
            "ranking": {
                "team_a_rank": team_a.rank,
                "team_b_rank": team_b.rank,
            },
            "recent_form": {
                "team_a_win_rate": team_a.recent_win_rate or team_a.win_rate,
                "team_b_win_rate": team_b.recent_win_rate or team_b.win_rate,
            },
            "historical": {
                "team_a_wins": 0,  # TODO: 从历史数据工具获取
                "team_b_wins": 0,
                "draws": 0,
            },
            "home_away": {
                "home_advantage": 0.10,  # TODO: 计算实际主场优势
                "away_disadvantage": 0.05,
            }
        }

        return reasoning_data
