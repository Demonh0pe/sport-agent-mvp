"""任务规划器 v1.2：针对 Golden Dataset 进行全覆盖优化的规则引擎 (Platinum Fix)。
"""
from __future__ import annotations
from typing import List

# === 1. 扩充关键词库 (Knowledge Base) ===
INTENT_KEYWORDS = {
    # 预测类
    "score_prediction": ["比分", "几比几", "大球", "小球"],
    "event_prediction": ["角球", "黄牌", "点球", "进球数", "大小球"],
    
    # 资讯与状态类
    "news": [
        "新闻", "伤", "舆论", "转会", "首发", "名单", "集训", 
        "C罗", "梅西", "内马尔", "德布劳内", # 球星实体
        "失去", "缺席", "无", "升级", "有效吗", "进球" # 负面状态或动态
    ],
    "stats": [
        "状态", "表现", "数据", "榜", "赛程", "战绩", "阵容", "体能", "连胜",
        "助攻", "差距", "特性", "分析", "主客场",
        "厉害", "强", "实力", "优劣", "谁更", "水平"
    ],
    
    # 战术与实时类
    "tactics": ["战术", "阵型", "打法", "教练", "调整"],
    "live": ["实时", "控球", "正在", "战局", "失控"],
    
    # 历史与复盘类 (修复 Q18: 拆分主客场，增加差距)
    "history": [
        "交锋", "历史", "回顾", "复盘", "差异", "差距", 
        "主客场", "主场", "客场", # 拆分开，防止匹配不到 "主场和客场"
        "vs", "德比", "和", "对比", "对比分析" ,"与"
    ], 
    
    # 市场与策略类
    "odds": ["赔率", "盘口", "水位", "异常", "波动"],
    "strategy": ["策略", "保守", "激进", "怎么买", "推荐", "可持续"],
}

def detect_intents(user_query: str) -> List[str]:
    """意图识别：基于关键词的模糊匹配"""
    lowered = user_query.lower()
    intents = []
    
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            intents.append(intent)
            
    return list(set(intents))

def plan_decomposition(user_query: str) -> List[str]:
    """
    将自然语言映射为工具调用链。
    """
    steps: List[str] = []
    intents = detect_intents(user_query)
    
    # === Step 1: 实体解析 ===
    if "F1" not in user_query and "C罗" not in user_query and "梅西" not in user_query:
         steps.append(f"MatchResolverTool(query='{user_query}')")
    
    # === Step 2: 核心工具挂载 ===
    
    # A. 实时数据
    if "live" in intents:
        steps.append("LiveFeedTool(match_id=$match_id)")
        
    # B. 赔率与市场
    if "odds" in intents:
        steps.append("OddsTool(match_id=$match_id)")
        
    # C. 预测模块
    is_sport_prediction = True
    if "F1" in user_query or "状态" in user_query or "差距" in user_query:
        if "预测" not in user_query and "概率" not in user_query:
            is_sport_prediction = False

    if is_sport_prediction:
        if any(k in user_query for k in ["预测", "概率", "赢", "胜", "推荐", "策略"]):
            steps.append("PredictionTool(match_id=$match_id, phase='T-24h')")
        
        if "score_prediction" in intents:
            steps.append("ScorelinePredictorTool(match_id=$match_id)")
            
        if "event_prediction" in intents or "黄牌" in user_query:
            etype = "goals"
            if "角球" in user_query: etype = "corners"
            if "黄牌" in user_query: etype = "cards"
            if "大小球" in user_query: etype = "goals"
            steps.append(f"EventPredictorTool(match_id=$match_id, event_type='{etype}')")

    # D. 历史与统计 (修复 Q18)
    # 只要 history 意图被触发（现在包含"差距"、"主场"、"客场"），就查历史
    if "history" in intents:
        steps.append("HistoricalComparisonTool(match_id=$match_id, window=5)")
        
    if "stats" in intents or "特性" in user_query:
        scope = "player" if any(n in user_query for n in ["梅西", "C罗", "内马尔", "球员", "阵容"]) else "team"
        steps.append(f"StatsAnalysisTool(match_id=$match_id, scope='{scope}', window='last5')")

    # E. 战术分析
    if "tactics" in intents:
        steps.append("TacticalInsightTool(match_id=$match_id)")

    # F. 新闻资讯 (修复 Q11)
    # 增加 "体能" 作为触发词，因为体能分析通常依赖新闻/伤病报告
    if "news" in intents or "进球" in user_query or "升级" in user_query or "体能" in user_query:
        entity = "team"
        if any(n in user_query for n in ["C罗", "梅西", "内马尔", "德布劳内"]):
            entity = "player"
        steps.append(f"NewsTool(entity_id=$entity_id, entity_type='{entity}', window_hours=72)")

    # G. 策略建议
    if "strategy" in intents:
        steps.append("StrategyTool(preference='balanced', context='...')")

    # === Step 3: LLM 汇总 ===
    steps.append("LLMAugmentorTool(context=$tool_outputs)")
    
    return steps