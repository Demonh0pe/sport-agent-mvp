"""
Agent功能模块

三个核心模块：
1. MatchQueryModule - 赛事查询
2. MatchAnalysisModule - 赛事分析
3. MatchSummaryModule - 赛事总结
"""
from .match_query import MatchQueryModule
from .match_analysis import MatchAnalysisModule
from .match_summary import MatchSummaryModule

__all__ = [
    "MatchQueryModule",
    "MatchAnalysisModule",
    "MatchSummaryModule"
]
