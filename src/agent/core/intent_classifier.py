"""
意图分类器 (Intent Classifier)

功能：
1. 规则匹配（快速、准确）
2. LLM兜底（灵活、智能）
3. 支持的意图：query, prediction, comparison, analysis, summary, clarification

按照 DATA_INTENT_GUIDE.md 设计
"""

import logging
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.shared.llm_client import llm_client

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """支持的意图类型"""
    QUERY = "query"  # 查询：比赛战绩、排名、赛程
    PREDICTION = "prediction"  # 预测：谁会赢、胜率
    COMPARISON = "comparison"  # 对比：A vs B、谁更强
    ANALYSIS = "analysis"  # 分析：状态、趋势、原因
    SUMMARY = "summary"  # 总结：概况、综述
    CLARIFICATION = "clarification"  # 澄清：不理解、需要更多信息
    UNKNOWN = "unknown"  # 未知


class IntentResult(BaseModel):
    """意图识别结果"""
    intent: Intent = Field(..., description="识别的意图")
    confidence: float = Field(..., description="置信度 0-1", ge=0, le=1)
    method: str = Field(..., description="识别方法：rule/llm")
    sub_intents: List[str] = Field(default_factory=list, description="子意图")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class IntentClassifier:
    """
    意图分类器
    
    策略：
    1. 优先使用规则匹配（快速、准确、免费）
    2. 规则不确定时使用LLM兜底（智能、灵活）
    
    设计原则：
    - 规则覆盖80%常见场景
    - LLM处理复杂/模糊场景
    - 始终返回置信度，用于下游决策
    """
    
    def __init__(self, use_llm_fallback: bool = True):
        """
        Args:
            use_llm_fallback: 是否启用LLM兜底
        """
        self.use_llm_fallback = use_llm_fallback
        
        # 规则库：关键词 -> 意图
        self.intent_patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[Intent, Dict[str, List[str]]]:
        """
        初始化意图识别模式
        
        结构：{Intent: {"keywords": [...], "exclusions": [...]}}
        """
        return {
            Intent.QUERY: {
                "keywords": [
                    # 中文
                    "最近", "近期", "比赛", "战绩", "赛程", "排名", "积分",
                    "对阵", "交锋", "历史", "记录", "几场", "什么时候",
                    # 英文
                    "recent", "match", "fixture", "standing", "rank", "record",
                    "schedule", "when", "history", "h2h"
                ],
                "exclusions": ["预测", "分析", "总结", "谁会赢", "谁更强"]
            },
            
            Intent.PREDICTION: {
                "keywords": [
                    # 中文
                    "预测", "谁会赢", "会赢吗", "能赢吗", "胜率", "概率",
                    "可能性", "会不会赢", "赢面", "胜算",
                    # 英文
                    "predict", "prediction", "who will win", "win rate",
                    "odds", "probability", "forecast"
                ],
                "exclusions": []
            },
            
            Intent.COMPARISON: {
                "keywords": [
                    # 中文
                    "对比", "比较", "谁更强", "vs", "versus", "还是",
                    "和", "哪个更", "哪个好", "差距", "优势", "劣势",
                    # 英文
                    "compare", "comparison", "vs", "versus", "better",
                    "stronger", "weaker", "difference"
                ],
                "exclusions": []
            },
            
            Intent.ANALYSIS: {
                "keywords": [
                    # 中文
                    "分析", "状态", "形势", "趋势", "原因", "为什么",
                    "怎么样", "如何", "评价", "优缺点", "问题",
                    # 英文
                    "analyze", "analysis", "form", "status", "trend",
                    "why", "how", "evaluation", "issue", "problem"
                ],
                "exclusions": ["总结", "概况"]
            },
            
            Intent.SUMMARY: {
                "keywords": [
                    # 中文
                    "总结", "概况", "综述", "简要", "概要", "整体",
                    "总的来说", "大致", "简述",
                    # 英文
                    "summary", "summarize", "overview", "brief",
                    "overall", "in general"
                ],
                "exclusions": []
            },
        }
    
    async def classify(self, query: str) -> IntentResult:
        """
        分类用户查询
        
        Args:
            query: 用户查询文本
            
        Returns:
            IntentResult
        """
        # 1. 尝试规则匹配
        result = self._rule_based_classify(query)
        
        # 2. 如果规则不确定且启用了LLM，使用LLM兜底
        if result.confidence < 0.7 and self.use_llm_fallback:
            logger.info(f"规则匹配置信度低 ({result.confidence:.2f})，使用LLM兜底")
            llm_result = await self._llm_based_classify(query)
            
            # 选择置信度更高的结果
            if llm_result.confidence > result.confidence:
                return llm_result
        
        return result
    
    def _rule_based_classify(self, query: str) -> IntentResult:
        """
        基于规则的意图分类
        
        算法：
        1. 计算每个意图的匹配分数
        2. 检查排除词
        3. 选择得分最高的意图
        """
        query_lower = query.lower()
        scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            
            # 关键词匹配
            keywords = patterns.get("keywords", [])
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            
            # 排除词检查
            exclusions = patterns.get("exclusions", [])
            for exclusion in exclusions:
                if exclusion in query_lower:
                    score -= 2  # 惩罚更重
            
            scores[intent] = max(0, score)
        
        # 选择得分最高的意图
        if scores:
            best_intent = max(scores, key=scores.get)
            best_score = scores[best_intent]
            total_keywords = len(self.intent_patterns[best_intent]["keywords"])
            
            # 归一化置信度
            confidence = min(1.0, best_score / (total_keywords * 0.3))
            
            if best_score > 0:
                logger.info(f"规则匹配: {best_intent.value} (置信度: {confidence:.2f})")
                return IntentResult(
                    intent=best_intent,
                    confidence=confidence,
                    method="rule",
                    metadata={"scores": scores}
                )
        
        # 无法匹配，返回UNKNOWN
        logger.info("规则匹配失败，返回UNKNOWN")
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            method="rule",
            metadata={"scores": scores}
        )
    
    async def _llm_based_classify(self, query: str) -> IntentResult:
        """
        基于LLM的意图分类
        
        使用LLM理解复杂/模糊的查询
        """
        system_prompt = """你是一个足球问答助手的意图分类器。

支持的意图类型：
- query: 查询比赛战绩、排名、赛程等事实信息
- prediction: 预测比赛结果、胜率
- comparison: 对比两个球队/球员的实力
- analysis: 分析球队状态、趋势、原因
- summary: 总结球队近期情况
- clarification: 查询不明确，需要更多信息

请只返回JSON格式：
{
    "intent": "意图类型",
    "confidence": 0.0-1.0,
    "reasoning": "简短的理由"
}
"""
        
        user_prompt = f"用户查询：{query}"
        
        try:
            response = await llm_client.generate(system_prompt, user_prompt)
            
            # 解析LLM响应
            import json
            # 提取JSON部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            
            result_dict = json.loads(json_str.strip())
            
            intent_str = result_dict.get("intent", "unknown")
            confidence = float(result_dict.get("confidence", 0.5))
            reasoning = result_dict.get("reasoning", "")
            
            # 转换为Intent枚举
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.UNKNOWN
            
            logger.info(f"LLM分类: {intent.value} (置信度: {confidence:.2f}, 理由: {reasoning})")
            
            return IntentResult(
                intent=intent,
                confidence=confidence,
                method="llm",
                metadata={"reasoning": reasoning}
            )
            
        except Exception as e:
            logger.error(f"LLM意图分类失败: {e}", exc_info=True)
            return IntentResult(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                method="llm",
                metadata={"error": str(e)}
            )
    
    def batch_classify(self, queries: List[str]) -> List[IntentResult]:
        """
        批量分类（同步，仅使用规则）
        
        Args:
            queries: 查询列表
            
        Returns:
            意图结果列表
        """
        return [self._rule_based_classify(q) for q in queries]


# 全局单例
intent_classifier = IntentClassifier()


# 便捷函数
async def classify_intent(query: str) -> IntentResult:
    """
    便捷函数：分类单个查询
    
    Usage:
        from src.agent.core.intent_classifier import classify_intent
        result = await classify_intent("曼联最近战绩如何？")
        print(result.intent, result.confidence)
    """
    return await intent_classifier.classify(query)


# 测试代码
if __name__ == "__main__":
    import sys
    import asyncio
    from pathlib import Path
    
    # 添加项目根目录到路径
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    async def test():
        test_queries = [
            # Query
            "曼联最近5场比赛战绩",
            "利物浦在英超排名第几",
            "曼联对利物浦的历史交锋记录",
            
            # Prediction
            "预测曼联对利物浦谁会赢",
            "曼联能赢吗",
            "利物浦的胜率是多少",
            
            # Comparison
            "曼联和利物浦谁更强",
            "对比一下拜仁和多特",
            "皇马vs巴萨哪个更厉害",
            
            # Analysis
            "分析一下曼联最近的状态",
            "利物浦为什么最近表现不好",
            "评价一下阿森纳的进攻",
            
            # Summary
            "总结曼联最近的情况",
            "简要说明利物浦的状态",
            "概况一下切尔西本赛季",
            
            # Unclear
            "球队",
            "怎么样",
        ]
        
        print("=" * 80)
        print("意图分类测试")
        print("=" * 80)
        
        for query in test_queries:
            result = await intent_classifier.classify(query)
            print(f"\n查询: {query}")
            print(f"意图: {result.intent.value}")
            print(f"置信度: {result.confidence:.2f}")
            print(f"方法: {result.method}")
    
    asyncio.run(test())

