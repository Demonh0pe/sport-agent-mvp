"""
澄清场景处理器 (Clarification Scenario)

功能：
1. 检测实体缺失（球队、联赛）
2. 检测意图不明
3. 提供候选建议
4. 生成澄清问题

按照 DATA_INTENT_GUIDE.md 设计
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from src.data_pipeline.entity_resolver import entity_resolver

logger = logging.getLogger(__name__)


class ClarificationType(str, Enum):
    """澄清类型"""
    MISSING_TEAM = "missing_team"  # 缺少球队信息
    MISSING_LEAGUE = "missing_league"  # 缺少联赛信息
    AMBIGUOUS_TEAM = "ambiguous_team"  # 球队名称模糊
    INTENT_UNCLEAR = "intent_unclear"  # 意图不明确
    INSUFFICIENT_INFO = "insufficient_info"  # 信息不足


class ClarificationResult(BaseModel):
    """澄清结果"""
    needs_clarification: bool = Field(description="是否需要澄清")
    clarification_type: Optional[ClarificationType] = Field(description="澄清类型")
    message: str = Field(description="澄清消息")
    candidates: List[Dict[str, Any]] = Field(default_factory=list, description="候选项")
    suggestions: List[str] = Field(default_factory=list, description="建议问题")


class ClarificationScenario:
    """
    澄清场景处理器
    
    核心流程：
    1. 分析查询，检测缺失信息
    2. 生成候选建议
    3. 构造澄清问题
    """
    
    def __init__(self):
        self.entity_resolver = entity_resolver
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保初始化"""
        if not self._initialized:
            await self.entity_resolver.initialize()
            self._initialized = True
    
    async def analyze(
        self, 
        query: str,
        detected_entities: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None
    ) -> ClarificationResult:
        """
        分析是否需要澄清
        
        Args:
            query: 用户查询
            detected_entities: 已检测的实体
            intent: 识别的意图
            
        Returns:
            ClarificationResult
        """
        await self._ensure_initialized()
        
        # 1. 检查实体缺失
        missing_entity_result = await self._check_missing_entities(
            query, detected_entities, intent
        )
        if missing_entity_result.needs_clarification:
            return missing_entity_result
        
        # 2. 检查意图不明
        if not intent or intent == "unknown":
            return self._generate_intent_clarification(query)
        
        # 3. 检查信息不足
        insufficient_info_result = self._check_insufficient_info(
            query, detected_entities, intent
        )
        if insufficient_info_result.needs_clarification:
            return insufficient_info_result
        
        # 4. 无需澄清
        return ClarificationResult(
            needs_clarification=False,
            clarification_type=None,
            message="查询清晰，无需澄清"
        )
    
    async def _check_missing_entities(
        self,
        query: str,
        detected_entities: Optional[Dict[str, Any]],
        intent: Optional[str]
    ) -> ClarificationResult:
        """检查实体缺失"""
        
        detected_entities = detected_entities or {}
        
        # 检测查询中是否提到了球队
        team_keywords = [
            "球队", "队", "俱乐部", "team", "club",
            "比赛", "对阵", "vs", "对", "match"
        ]
        mentions_team = any(kw in query.lower() for kw in team_keywords)
        
        # 如果提到了球队但没有检测到
        if mentions_team and not detected_entities.get("team"):
            # 尝试搜索可能的球队
            candidates = await self._search_possible_teams(query)
            
            if candidates:
                return ClarificationResult(
                    needs_clarification=True,
                    clarification_type=ClarificationType.AMBIGUOUS_TEAM,
                    message=self._format_team_candidates(candidates),
                    candidates=candidates
                )
            else:
                return ClarificationResult(
                    needs_clarification=True,
                    clarification_type=ClarificationType.MISSING_TEAM,
                    message=self._format_missing_team_message(),
                    suggestions=await self._get_team_suggestions()
                )
        
        # 检测联赛缺失
        league_keywords = ["联赛", "league", "比赛", "积分榜"]
        mentions_league = any(kw in query.lower() for kw in league_keywords)
        
        if mentions_league and not detected_entities.get("league"):
            if intent in ["standing", "rank", "table"]:
                return ClarificationResult(
                    needs_clarification=True,
                    clarification_type=ClarificationType.MISSING_LEAGUE,
                    message=self._format_missing_league_message(),
                    suggestions=await self._get_league_suggestions()
                )
        
        # 无需澄清
        return ClarificationResult(
            needs_clarification=False,
            clarification_type=None,
            message=""
        )
    
    async def _search_possible_teams(self, query: str) -> List[Dict]:
        """搜索可能的球队"""
        # 提取查询中最长的词作为搜索关键词
        import re
        words = re.split(r'[\s,，、。！？：；]+', query)
        words = [w for w in words if len(w) >= 2]
        
        if not words:
            return []
        
        # 取最长的词
        max_word = max(words, key=len)
        
        # 搜索球队
        results = await self.entity_resolver.search_teams(max_word, limit=5)
        return results
    
    async def _get_team_suggestions(self) -> List[str]:
        """获取球队建议"""
        suggestions = []
        
        # 获取每个联赛的热门球队
        leagues = await self.entity_resolver.get_all_leagues()
        
        for league in leagues[:3]:  # 只取前3个联赛
            teams = await self.entity_resolver.get_all_teams(league['id'])
            if teams:
                suggestions.append(
                    f"- {league['name']}: {teams[0]['name']}, {teams[1]['name']}, ..."
                )
        
        return suggestions
    
    async def _get_league_suggestions(self) -> List[str]:
        """获取联赛建议"""
        leagues = await self.entity_resolver.get_all_leagues()
        return [f"- {league['name']} ({league['id']})" for league in leagues]
    
    def _format_team_candidates(self, candidates: List[Dict]) -> str:
        """格式化球队候选列表"""
        msg = "我找到了以下可能的球队，请问您是指哪一个？\n\n"
        
        for i, candidate in enumerate(candidates, 1):
            msg += f"{i}. {candidate['name']} ({candidate['id']})\n"
        
        msg += "\n请提供更具体的球队名称。"
        return msg
    
    def _format_missing_team_message(self) -> str:
        """格式化缺少球队的消息"""
        return """抱歉，我没有找到您提到的球队。

您可以查询以下联赛的球队：
- 英超 (Premier League)
- 德甲 (Bundesliga)
- 西甲 (La Liga)
- 意甲 (Serie A)
- 法甲 (Ligue 1)

请提供完整的球队名称，例如：
- 曼联 / Manchester United
- 拜仁 / Bayern München
- 皇马 / Real Madrid
"""
    
    def _format_missing_league_message(self) -> str:
        """格式化缺少联赛的消息"""
        return """请告诉我您想查询哪个联赛？

支持的联赛：
- 英超 (Premier League / EPL)
- 德甲 (Bundesliga / BL1)
- 西甲 (La Liga / PD)
- 意甲 (Serie A / SA)
- 法甲 (Ligue 1 / FL1)
- 欧冠 (Champions League / UCL)
"""
    
    def _generate_intent_clarification(self, query: str) -> ClarificationResult:
        """生成意图不明的澄清"""
        return ClarificationResult(
            needs_clarification=True,
            clarification_type=ClarificationType.INTENT_UNCLEAR,
            message=self._format_intent_unclear_message(),
            suggestions=[
                "查询最近的比赛战绩",
                "预测比赛结果",
                "对比两支球队",
                "分析球队状态",
                "查看积分榜排名"
            ]
        )
    
    def _format_intent_unclear_message(self) -> str:
        """格式化意图不明的消息"""
        return """抱歉，我不太理解您的问题。

您可以问我：

[查询]：
- 某球队最近的比赛战绩
- 某球队在联赛中的排名
- 两支球队的历史交锋

[预测]：
- 预测某场比赛的结果
- 某球队的胜率

[对比]：
- 对比两支球队的实力
- A vs B 谁更强

[分析]：
- 分析某球队的近期状态
- 评价某球队的表现

请提供更具体的问题。
"""
    
    def _check_insufficient_info(
        self,
        query: str,
        detected_entities: Optional[Dict[str, Any]],
        intent: Optional[str]
    ) -> ClarificationResult:
        """检查信息是否充足"""
        
        detected_entities = detected_entities or {}
        
        # 对比意图需要两支球队
        if intent in ["comparison", "predict"]:
            if not detected_entities.get("team_b"):
                return ClarificationResult(
                    needs_clarification=True,
                    clarification_type=ClarificationType.INSUFFICIENT_INFO,
                    message="对比或预测需要指定两支球队。\n\n例如：\n- 曼联对利物浦\n- 拜仁 vs 多特\n- Real Madrid 和 Barcelona"
                )
        
        return ClarificationResult(
            needs_clarification=False,
            clarification_type=None,
            message=""
        )


# 全局单例
clarification_scenario = ClarificationScenario()


# 便捷函数
async def check_clarification(
    query: str,
    entities: Optional[Dict] = None,
    intent: Optional[str] = None
) -> ClarificationResult:
    """
    便捷函数：检查是否需要澄清
    
    Usage:
        from src.agent.scenarios.clarification_scenario import check_clarification
        result = await check_clarification("球队")
        if result.needs_clarification:
            print(result.message)
    """
    return await clarification_scenario.analyze(query, entities, intent)


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
        print("澄清场景测试")
        print("=" * 80)
        
        test_cases = [
            # 缺少球队
            ("球队最近怎么样", None, "query"),
            ("查询比赛", None, "query"),
            
            # 球队模糊
            ("联最近战绩", None, "query"),  # "联"可能是曼联、国联等
            
            # 意图不明
            ("怎么样", None, None),
            ("好不好", None, None),
            
            # 信息不足
            ("曼联能赢吗", {"team": "Manchester United"}, "prediction"),
            
            # 清晰查询
            ("曼联最近5场比赛", {"team": "Manchester United"}, "query"),
        ]
        
        for query, entities, intent in test_cases:
            print(f"\n查询: {query}")
            print(f"实体: {entities}")
            print(f"意图: {intent}")
            print("-" * 80)
            
            result = await clarification_scenario.analyze(query, entities, intent)
            
            if result.needs_clarification:
                print(f"[?] 需要澄清: {result.clarification_type}")
                print(f"\n{result.message}")
                if result.candidates:
                    print(f"\n候选项: {len(result.candidates)} 个")
            else:
                print("[OK] 无需澄清")
    
    asyncio.run(test())

