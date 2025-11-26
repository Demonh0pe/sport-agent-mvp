"""
对比场景处理器 (Comparison Scenario)

功能：
1. 封装 H2H（Head-to-Head）对比
2. 整合统计数据对比
3. 生成结构化对比报告

按照 DATA_INTENT_GUIDE.md 设计
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from src.agent.tools.match_tool import match_tool
from src.agent.tools.stats_tool import stats_tool
from src.data_pipeline.entity_resolver import entity_resolver

logger = logging.getLogger(__name__)


class ComparisonResult(BaseModel):
    """对比结果"""
    team_a: str
    team_b: str
    h2h_summary: str = Field(description="历史交锋总结")
    stats_comparison: Dict[str, Any] = Field(description="统计数据对比")
    conclusion: str = Field(description="结论")
    confidence: float = Field(description="结论置信度 0-1")


class ComparisonScenario:
    """
    对比场景处理器
    
    核心流程：
    1. 解析两支球队
    2. 获取历史交锋（H2H）
    3. 获取统计数据
    4. 生成对比报告
    """
    
    def __init__(self):
        self.entity_resolver = entity_resolver
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保初始化"""
        if not self._initialized:
            await self.entity_resolver.initialize()
            self._initialized = True
    
    async def execute(
        self, 
        team_a_name: str, 
        team_b_name: str,
        league_id: Optional[str] = None
    ) -> ComparisonResult:
        """
        执行对比分析
        
        Args:
            team_a_name: 球队A名称
            team_b_name: 球队B名称
            league_id: 可选，联赛ID
            
        Returns:
            ComparisonResult
        """
        await self._ensure_initialized()
        
        # 1. 解析球队
        team_a_id = await self.entity_resolver.resolve_team(team_a_name)
        team_b_id = await self.entity_resolver.resolve_team(team_b_name)
        
        if not team_a_id or not team_b_id:
            raise ValueError(f"无法解析球队: {team_a_name}, {team_b_name}")
        
        team_a_info = await self.entity_resolver.get_team_info(team_a_id)
        team_b_info = await self.entity_resolver.get_team_info(team_b_id)
        
        logger.info(f"对比分析: {team_a_info['name']} vs {team_b_info['name']}")
        
        # 2. 获取历史交锋（传入team_id以便精确匹配）
        h2h_data = await self._get_h2h(
            team_a_info['name'], team_b_info['name'],
            team_a_id, team_b_id
        )
        
        # 3. 获取统计数据
        stats_a = await self._get_team_stats(team_a_info['name'])
        stats_b = await self._get_team_stats(team_b_info['name'])
        
        # 4. 生成对比
        comparison = self._generate_comparison(
            team_a_info, team_b_info,
            h2h_data, stats_a, stats_b
        )
        
        return comparison
    
    async def _get_h2h(
        self, 
        team_a: str, 
        team_b: str,
        team_a_id: Optional[str] = None,
        team_b_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取历史交锋数据
        
        Returns:
            {
                "matches": List,  # 比赛列表
                "summary": str,   # 摘要
            }
        """
        try:
            # 获取历史交锋记录
            matches = await match_tool.get_head_to_head_matches(team_a, team_b, limit=5)
            
            if not matches:
                return {
                    "matches": [],
                    "summary": f"{team_a} 和 {team_b} 暂无历史交锋记录"
                }
            
            # 统计战绩
            team_a_wins = 0
            team_b_wins = 0
            draws = 0
            
            match_summaries = []
            for match in matches:
                # 判断主客场 - 如果有team_id则精确匹配，否则模糊匹配
                if team_a_id:
                    is_team_a_home = match.home_team_id == team_a_id
                else:
                    is_team_a_home = team_a.lower() in match.home_team_id.lower()
                
                if match.result == 'D':
                    draws += 1
                    result_text = "平局"
                elif match.result == 'H':
                    if is_team_a_home:
                        team_a_wins += 1
                        result_text = f"{team_a} 胜"
                    else:
                        team_b_wins += 1
                        result_text = f"{team_b} 胜"
                else:  # result == 'A'
                    if is_team_a_home:
                        team_b_wins += 1
                        result_text = f"{team_b} 胜"
                    else:
                        team_a_wins += 1
                        result_text = f"{team_a} 胜"
                
                match_summaries.append(
                    f"{match.match_date.strftime('%Y-%m-%d')}: "
                    f"{match.home_team_id} {match.home_score}:{match.away_score} {match.away_team_id} "
                    f"({result_text})"
                )
            
            summary = f"""
近{len(matches)}场交锋记录：
- {team_a}: {team_a_wins}胜
- {team_b}: {team_b_wins}胜  
- 平局: {draws}场

详细记录：
""" + "\n".join([f"- {s}" for s in match_summaries])
            
            return {
                "matches": matches,
                "summary": summary.strip()
            }
        except Exception as e:
            logger.error(f"获取H2H数据失败: {e}")
            return {
                "matches": [],
                "summary": "历史交锋数据获取失败"
            }
    
    async def _get_team_stats(self, team_name: str) -> Dict[str, Any]:
        """获取球队统计数据"""
        try:
            # TODO: 调用真实的 stats_tool
            return {
                "team": team_name,
                "available": False
            }
        except Exception as e:
            logger.error(f"获取统计数据失败 ({team_name}): {e}")
            return {
                "team": team_name,
                "available": False,
                "error": str(e)
            }
    
    def _generate_comparison(
        self,
        team_a_info: Dict,
        team_b_info: Dict,
        h2h_data: Dict,
        stats_a: Dict,
        stats_b: Dict
    ) -> ComparisonResult:
        """
        生成对比报告
        
        整合所有数据，生成结构化报告
        """
        # 简化版本：基于可用数据生成报告
        conclusion = f"""
基于当前可用数据，{team_a_info['name']} 和 {team_b_info['name']} 的对比如下：

【基本信息】
- {team_a_info['name']}: 联赛 {team_a_info['league_id']}
- {team_b_info['name']}: 联赛 {team_b_info['league_id']}

【历史交锋】
{h2h_data['summary']}

【结论】
两支球队实力接近，需要更多数据进行深入分析。

建议：
1. 查看最近5场比赛战绩
2. 对比积分榜排名
3. 分析主客场优势
"""
        
        return ComparisonResult(
            team_a=team_a_info['name'],
            team_b=team_b_info['name'],
            h2h_summary=h2h_data['summary'],
            stats_comparison={
                "team_a": stats_a,
                "team_b": stats_b
            },
            conclusion=conclusion.strip(),
            confidence=0.5  # 数据有限，置信度较低
        )


# 全局单例
comparison_scenario = ComparisonScenario()


# 便捷函数
async def compare_teams(
    team_a: str, 
    team_b: str,
    league_id: Optional[str] = None
) -> ComparisonResult:
    """
    便捷函数：对比两支球队
    
    Usage:
        from src.agent.scenarios.comparison_scenario import compare_teams
        result = await compare_teams("Manchester United", "Liverpool")
        print(result.conclusion)
    """
    return await comparison_scenario.execute(team_a, team_b, league_id)


# 测试代码
if __name__ == "__main__":
    import sys
    import asyncio
    from pathlib import Path
    
    # 添加项目根目录到路径
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    async def test():
        print("=" * 80)
        print("对比场景测试")
        print("=" * 80)
        
        test_cases = [
            ("Manchester United", "Liverpool"),
            ("曼联", "利物浦"),
            ("Real Madrid", "Barcelona"),
        ]
        
        for team_a, team_b in test_cases:
            try:
                print(f"\n对比: {team_a} vs {team_b}")
                print("-" * 80)
                
                result = await comparison_scenario.execute(team_a, team_b)
                
                print(f"\n{result.conclusion}")
                print(f"\n置信度: {result.confidence:.2f}")
            except Exception as e:
                print(f"❌ 对比失败: {e}")
    
    asyncio.run(test())

