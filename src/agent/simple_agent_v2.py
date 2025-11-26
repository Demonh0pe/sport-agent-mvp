"""
简化版Agent v2 - 零硬编码版本

核心改进：
1. 使用EntityResolver替代硬编码映射
2. 所有实体解析动态从数据库加载
3. 支持澄清场景（实体不明时提供建议）
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Any

from src.agent.modules.match_query import MatchQueryModule
from src.agent.modules.match_analysis import MatchAnalysisModule
from src.agent.modules.match_summary import MatchSummaryModule
from src.data_pipeline.entity_resolver import entity_resolver

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    success: bool
    answer: str
    intent: str  # 识别的意图
    entities: Dict[str, Any]  # 提取的实体
    module_used: str  # 使用的模块
    metadata: Dict[str, Any] = None  # 元数据


class SimpleAgentV2:
    """
    简化版Agent v2 - 零硬编码
    
    核心能力：
    1. 意图识别（查询/分析/总结）
    2. 实体提取（球队、联赛）- 使用EntityResolver
    3. 路由到对应模块
    4. 澄清处理（实体不明时提供建议）
    """

    def __init__(self):
        # 初始化三个模块
        self.query_module = MatchQueryModule()
        self.analysis_module = MatchAnalysisModule()
        self.summary_module = MatchSummaryModule()

        # 使用EntityResolver（零硬编码）
        self.entity_resolver = entity_resolver
        self._initialized = False

        logger.info("[SimpleAgentV2] Initialized with 3 modules + EntityResolver")

    async def _ensure_initialized(self):
        """确保EntityResolver已初始化"""
        if not self._initialized:
            await self.entity_resolver.initialize()
            self._initialized = True

    async def chat(self, user_input: str) -> AgentResponse:
        """
        处理用户输入
        
        流程：
        1. 意图识别
        2. 实体提取
        3. 路由到对应模块
        4. 返回结果
        """
        # 确保初始化
        await self._ensure_initialized()

        logger.info(f"[SimpleAgentV2] 收到查询: {user_input}")

        # 1. 意图识别
        intent = self._classify_intent(user_input)
        logger.info(f"[SimpleAgentV2] 意图识别: {intent}")

        # 2. 实体提取
        entities = await self._extract_entities(user_input)
        logger.info(f"[SimpleAgentV2] 实体提取: {entities}")

        # 3. 检查是否需要澄清
        if entities.get("needs_clarification"):
            clarification_msg = await self._generate_clarification(
                user_input, entities
            )
            return AgentResponse(
                success=True,
                answer=clarification_msg,
                intent="clarification",
                entities=entities,
                module_used="clarification"
            )

        # 4. 路由到对应模块
        try:
            if intent == "summary":
                answer = await self.summary_module.summarize(user_input, entities)
                module_used = "MatchSummaryModule"
            elif intent == "analysis":
                answer = await self.analysis_module.analyze(user_input, entities)
                module_used = "MatchAnalysisModule"
            else:  # query
                answer = await self.query_module.query(user_input, entities)
                module_used = "MatchQueryModule"

            return AgentResponse(
                success=True,
                answer=answer,
                intent=intent,
                entities=entities,
                module_used=module_used
            )
        except Exception as e:
            logger.error(f"[SimpleAgentV2] 执行失败: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                answer=f"抱歉，处理您的请求时出现了错误：{str(e)}",
                intent=intent,
                entities=entities,
                module_used="error"
            )

    def _classify_intent(self, query: str) -> str:
        """
        意图分类（基于关键词）
        
        优先级：总结 > 分析 > 查询
        """
        query_lower = query.lower()

        # 总结类关键词
        summary_keywords = [
            "总结", "概况", "综述", "简要", "概要", "整体",
            "summary", "overview", "brief"
        ]
        for keyword in summary_keywords:
            if keyword in query_lower:
                return "summary"

        # 分析类关键词
        analysis_keywords = [
            "分析", "预测", "比较", "对比", "谁更强", "谁会赢",
            "如何", "怎么样", "状态", "form", "analyze", "prediction",
            "compare", "vs", "对"
        ]
        for keyword in analysis_keywords:
            if keyword in query_lower:
                return "analysis"

        # 默认为查询
        return "query"

    async def _extract_entities(self, query: str) -> Dict[str, Any]:
        """
        实体提取（使用EntityResolver，零硬编码）
        
        Returns:
            {
                team: 第一个球队（用于单队查询）
                team_a: 第一个球队（用于对比）
                team_b: 第二个球队（用于对比）
                league: 联赛
                needs_clarification: 是否需要澄清
                clarification_candidates: 澄清候选项
            }
        """
        entities = {}
        
        # 提取球队
        # 策略：将查询分词，尝试解析每个片段
        found_teams = []
        found_team_ids = set()  # 去重
        
        # 简单分词：按空格、标点分割
        import re
        words = re.split(r'[\s,，、。！？：；]+', query)
        
        for word in words:
            if len(word) < 2:  # 跳过太短的词
                continue
            
            # 尝试解析为球队
            team_id = await self.entity_resolver.resolve_team(
                word, source="user_query"
            )
            if team_id and team_id not in found_team_ids:
                team_info = await self.entity_resolver.get_team_info(team_id)
                found_teams.append({
                    "id": team_id,
                    "name": team_info["name"],
                    "query": word
                })
                found_team_ids.add(team_id)
        
        # 分配球队角色
        if len(found_teams) >= 1:
            entities['team'] = found_teams[0]['name']
            entities['team_a'] = found_teams[0]['name']
            entities['team_id'] = found_teams[0]['id']
        
        if len(found_teams) >= 2:
            entities['team_b'] = found_teams[1]['name']
            entities['team_b_id'] = found_teams[1]['id']
        
        # 提取联赛
        for word in words:
            if len(word) < 2:
                continue
            
            league_id = await self.entity_resolver.resolve_league(
                word, source="user_query"
            )
            if league_id:
                league_info = await self.entity_resolver.get_league_info(league_id)
                entities['league'] = league_info['name']
                entities['league_id'] = league_id
                break
        
        # 检查是否需要澄清
        # 如果查询中提到了球队相关词汇但没找到球队，需要澄清
        team_related_keywords = ["球队", "队", "俱乐部", "team", "club"]
        mentions_team = any(kw in query.lower() for kw in team_related_keywords)
        
        if mentions_team and not found_teams:
            entities['needs_clarification'] = True
            entities['clarification_type'] = 'team_not_found'
            
            # 提供搜索建议
            # 尝试搜索查询中的关键词
            max_word = max(words, key=len) if words else ""
            if len(max_word) >= 2:
                candidates = await self.entity_resolver.search_teams(max_word, limit=5)
                entities['clarification_candidates'] = candidates
        
        return entities

    async def _generate_clarification(
        self, 
        query: str, 
        entities: Dict[str, Any]
    ) -> str:
        """
        生成澄清消息
        
        当实体不明时，提供候选建议
        """
        clarification_type = entities.get('clarification_type')
        
        if clarification_type == 'team_not_found':
            msg = "抱歉，我没有找到您提到的球队。\n\n"
            
            candidates = entities.get('clarification_candidates', [])
            if candidates:
                msg += "您是指以下球队中的哪一个吗？\n\n"
                for i, candidate in enumerate(candidates[:5], 1):
                    msg += f"{i}. {candidate['name']} ({candidate['id']})\n"
                msg += "\n请明确指定球队名称。"
            else:
                # 没有候选，显示所有可用球队
                msg += "您可以查询以下联赛的球队：\n\n"
                leagues = await self.entity_resolver.get_all_leagues()
                for league in leagues:
                    msg += f"• {league['name']}\n"
                msg += "\n请提供具体的球队名称。"
            
            return msg
        
        # 默认帮助信息
        return self._get_help_message()

    def _get_help_message(self) -> str:
        """获取帮助信息"""
        return """抱歉，我不太理解您的问题。

您可以问我：

📊 **查询类**：
- 曼联最近5场比赛战绩
- 利物浦在英超排名第几
- 曼联对利物浦的历史交锋

🔍 **分析类**：
- 分析一下曼联最近的状态
- 曼联和利物浦谁更强
- 预测曼联对利物浦谁会赢

📝 **总结类**：
- 总结曼联最近的情况
- 简要说明利物浦的状态
"""


# 便捷函数
async def chat(user_input: str) -> str:
    """
    便捷函数：快速调用Agent
    
    Usage:
        from src.agent.simple_agent_v2 import chat
        response = await chat("曼联最近战绩如何？")
    """
    agent = SimpleAgentV2()
    response = await agent.chat(user_input)
    return response.answer


# 测试入口
if __name__ == "__main__":
    async def test():
        agent = SimpleAgentV2()
        
        test_queries = [
            "曼联最近5场比赛战绩",
            "利物浦在英超中处于什么地位",
            "分析一下曼联最近的状态",
            "总结曼联最近的情况",
        ]
        
        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"查询: {query}")
            print(f"{'='*80}")
            
            response = await agent.chat(query)
            
            print(f"意图: {response.intent}")
            print(f"实体: {response.entities}")
            print(f"模块: {response.module_used}")
            print(f"\n回答:\n{response.answer}")
    
    asyncio.run(test())

