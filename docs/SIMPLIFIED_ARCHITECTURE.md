# 简化版Agent架构设计

**目标**: 2周内完成3个核心功能模块，全部使用本地大模型

---

## 一、整体架构（极简版）

```
用户输入: "曼联最近状态如何？"
    ↓
[1. 意图识别] - 简单规则匹配
    ↓
[2. 模块路由] - 3个模块选择
    ↓
┌─────────────┬─────────────┬─────────────┐
│ 赛事查询     │ 赛事分析     │ 赛事总结     │
│ (Query)     │ (Analysis)  │ (Summary)   │
└─────────────┴─────────────┴─────────────┘
    ↓
[3. 数据获取] - 调用现有工具
    ↓
[4. LLM生成] - Ollama本地模型
    ↓
结构化输出
```

---

## 二、3个核心模块

### 模块1: 赛事查询 (Match Query)

**用户场景**：
- "曼联最近5场比赛战绩"
- "利物浦在英超排名第几"
- "曼联对利物浦的历史交锋"
- "查询本周末有哪些比赛"

**核心功能**：
- 查询球队战绩
- 查询积分榜排名
- 查询历史交锋
- 查询比赛日程

**实现方式**：
```python
# src/agent/modules/match_query.py

class MatchQueryModule:
    """
    赛事查询模块

    输入：用户查询 + 实体（球队、联赛、时间）
    输出：结构化数据 + 自然语言描述
    """

    async def execute(self, query: str, entities: Dict) -> QueryResult:
        # 1. 识别查询类型
        query_type = self._detect_query_type(query)
        # "recent_matches" / "standings" / "h2h" / "schedule"

        # 2. 调用对应工具
        if query_type == "recent_matches":
            data = await match_tool.get_recent_matches(
                team_name=entities['team'],
                limit=5
            )
        elif query_type == "standings":
            data = await standings_tool.get_team_standing(
                team_name=entities['team'],
                league_name=entities.get('league')
            )
        elif query_type == "h2h":
            data = await self._get_h2h(entities['team_a'], entities['team_b'])

        # 3. 用LLM美化输出
        formatted_output = await self._format_with_llm(query, data)

        return QueryResult(
            raw_data=data,
            formatted_text=formatted_output,
            query_type=query_type
        )

    async def _format_with_llm(self, query: str, data: str) -> str:
        """用本地LLM格式化输出"""
        system_prompt = """你是一个足球数据助手。

任务：将查询数据用简洁、清晰的方式呈现给用户。

要求：
1. 使用表格或列表展示数据
2. 突出关键信息（战绩、排名、胜率）
3. 简洁明了，不要冗长
"""

        user_prompt = f"""
用户问：{query}

数据：
{data}

请格式化输出。
"""

        return await llm_client.generate(system_prompt, user_prompt)
```

**输出示例**：
```
📊 曼联近5场战绩

| 日期 | 对手 | 比分 | 结果 |
|------|------|------|------|
| 11-20 | 切尔西 | 1-2 | 负 ❌ |
| 11-15 | 阿森纳 | 1-1 | 平 ⚖️ |
| 11-10 | 热刺 | 2-1 | 胜 ✅ |
| 11-05 | 莱斯特 | 0-1 | 负 ❌ |
| 11-01 | 纽卡 | 1-1 | 平 ⚖️ |

📈 战绩统计：
- 1胜2平2负，胜率20%
- 进5球，失6球
- 近期走势：LWDLL（连续2场不胜）
```

---

### 模块2: 赛事分析 (Match Analysis)

**用户场景**：
- "分析一下曼联最近的状态"
- "曼联和利物浦谁更强？"
- "为什么利物浦排名第一？"
- "曼联对利物浦谁会赢？"

**核心功能**：
- 球队状态分析
- 两队对比分析
- 排名原因分析
- 比赛预测分析

**实现方式**：
```python
# src/agent/modules/match_analysis.py

class MatchAnalysisModule:
    """
    赛事分析模块

    使用已创建的：
    - DataAnalyzer: 数据提取和对比
    - ReasoningEngine: 深度推理
    """

    def __init__(self):
        self.data_analyzer = DataAnalyzer()
        self.reasoning_engine = ReasoningEngine()

    async def execute(self, query: str, entities: Dict) -> AnalysisResult:
        # 1. 识别分析类型
        analysis_type = self._detect_analysis_type(query)
        # "team_status" / "comparison" / "prediction" / "ranking_reason"

        # 2. 收集数据
        tool_results = await self._collect_data(entities, analysis_type)

        # 3. 数据分析（结构化）
        structured_data = self.data_analyzer.extract_structured_data(tool_results)

        # 4. 深度推理
        if analysis_type == "comparison" or analysis_type == "prediction":
            # 对比分析
            team_a = entities['team_a']
            team_b = entities['team_b']

            comparisons = self.data_analyzer.multi_dimensional_comparison(
                structured_data[team_a],
                structured_data[team_b]
            )

            # 推理引擎分析
            reasoning_data = self.data_analyzer.prepare_for_reasoning(
                structured_data,
                comparisons
            )

            reasoning_result = await self.reasoning_engine.analyze_match_prediction(
                query=query,
                structured_data=reasoning_data,
                comparisons=comparisons
            )

        # 5. 用LLM生成自然语言分析
        analysis_text = await self._generate_analysis(
            query,
            structured_data,
            reasoning_result if 'reasoning_result' in locals() else None
        )

        return AnalysisResult(
            analysis_type=analysis_type,
            structured_data=structured_data,
            reasoning=reasoning_result if 'reasoning_result' in locals() else None,
            analysis_text=analysis_text
        )

    async def _generate_analysis(
        self,
        query: str,
        data: Dict,
        reasoning: Optional[ReasoningResult]
    ) -> str:
        """用LLM生成深度分析"""

        system_prompt = """你是一个资深的足球数据分析师。

分析要求：
1. **多维度**：从排名、状态、进攻、防守等多个角度分析
2. **有逻辑**：数据 → 分析 → 结论，清晰的推理链
3. **量化表达**：用具体数字和百分比，不要模糊表达
4. **关键洞察**：找出最核心的1-2个问题或优势

输出格式：
- 使用emoji增强可读性
- 分层展示（核心结论 → 数据支撑 → 详细分析）
- 简洁有力，避免废话
"""

        # 构建用户prompt
        user_prompt = f"用户问：{query}\n\n"
        user_prompt += f"数据：\n{self._format_data_for_llm(data)}\n\n"

        if reasoning:
            user_prompt += f"推理结果：\n{reasoning.reasoning_trace}\n\n"

        user_prompt += "请进行深度分析。"

        return await llm_client.generate(system_prompt, user_prompt)
```

**输出示例**：
```
🔍 曼联状态分析

📉 核心结论：曼联目前处于低迷期

📊 数据支撑：
1. **战绩糟糕**
   - 近5场：1胜2平2负（胜率20%）
   - 排名：第15位（19分）
   - 与榜首利物浦差距：10分（51%）

2. **进攻乏力**
   - 近5场仅进5球（场均1球）
   - 创造机会少，把握能力差

3. **防守不稳**
   - 近5场丢6球
   - 关键时刻容易丢球

⚠️ 核心问题：
1. **战术混乱**：滕哈赫的4-2-3-1不适合球队
2. **球员状态**：核心球员拉什福德、费尔南德斯低迷
3. **赛程压力**：连续征战欧冠，体能透支

💡 建议：
- 短期：调整战术，回收防守
- 长期：冬窗引援，补强锋线
```

---

### 模块3: 赛事总结 (Match Summary)

**用户场景**：
- "总结一下曼联vs利物浦这场比赛"
- "简要说明曼联最近的情况"
- "快速了解英超积分榜情况"

**核心功能**：
- 单场比赛总结
- 球队阶段性总结
- 联赛整体概况

**实现方式**：
```python
# src/agent/modules/match_summary.py

class MatchSummaryModule:
    """
    赛事总结模块

    特点：简洁、快速、要点清晰
    """

    async def execute(self, query: str, entities: Dict) -> SummaryResult:
        # 1. 识别总结类型
        summary_type = self._detect_summary_type(query)
        # "single_match" / "team_period" / "league_overview"

        # 2. 收集关键信息
        data = await self._collect_key_info(entities, summary_type)

        # 3. 用LLM生成摘要
        summary_text = await self._generate_summary(query, data, summary_type)

        return SummaryResult(
            summary_type=summary_type,
            summary_text=summary_text,
            key_points=self._extract_key_points(summary_text)
        )

    async def _generate_summary(
        self,
        query: str,
        data: str,
        summary_type: str
    ) -> str:
        """用LLM生成摘要"""

        system_prompt = """你是一个足球新闻编辑。

任务：将比赛或球队信息总结成简洁的摘要。

要求：
1. **简洁**：控制在100-200字
2. **要点清晰**：3-5个关键点
3. **客观**：基于数据，不主观评价
4. **结构化**：使用emoji和列表

格式示例：
⚽ 比赛总结：
- 比分：曼联 1-2 利物浦
- 关键：萨拉赫梅开二度
- 影响：利物浦继续领跑，曼联连续2场不胜
"""

        user_prompt = f"""
用户需求：{query}

信息：
{data}

请生成简洁的摘要。
"""

        return await llm_client.generate(
            system_prompt,
            user_prompt,
            temperature=0.5  # 降低温度，更客观
        )
```

**输出示例**：
```
⚽ 曼联vs利物浦 比赛总结

📋 基本信息：
- 比分：曼联 1-2 利物浦（客胜）
- 时间：2024-11-20
- 联赛：英超第12轮

🎯 关键时刻：
- 15' 萨拉赫首开纪录
- 38' 拉什福德扳平比分
- 67' 萨拉赫梅开二度锁定胜局

📊 数据亮点：
- 控球率：曼联 45% vs 利物浦 55%
- 射门：曼联 8次 vs 利物浦 14次
- 萨拉赫全场最佳

💭 影响：
- 利物浦继续领跑积分榜（29分）
- 曼联连续2场不胜，排名第15（19分）
```

---

## 三、统一的Agent入口

```python
# src/agent/simple_agent.py

class SimpleAgent:
    """
    简化版Agent

    只做3件事：
    1. 识别意图（查询/分析/总结）
    2. 提取实体（球队、联赛、时间）
    3. 路由到对应模块
    """

    def __init__(self):
        self.query_module = MatchQueryModule()
        self.analysis_module = MatchAnalysisModule()
        self.summary_module = MatchSummaryModule()

    async def chat(self, user_input: str) -> str:
        """
        主接口

        流程：
        1. 意图识别（简单规则）
        2. 实体提取（简单映射）
        3. 模块路由
        4. 返回结果
        """

        # 1. 意图识别
        intent = self._classify_intent(user_input)

        # 2. 实体提取
        entities = self._extract_entities(user_input)

        # 3. 路由到对应模块
        if intent == "query":
            result = await self.query_module.execute(user_input, entities)
            return result.formatted_text

        elif intent == "analysis":
            result = await self.analysis_module.execute(user_input, entities)
            return result.analysis_text

        elif intent == "summary":
            result = await self.summary_module.execute(user_input, entities)
            return result.summary_text

        else:
            return "抱歉，我不太理解您的问题。您可以问我：\n" \
                   "- 查询：曼联最近战绩\n" \
                   "- 分析：曼联和利物浦对比\n" \
                   "- 总结：总结曼联最近情况"

    def _classify_intent(self, query: str) -> str:
        """
        简单的意图识别（基于关键词）
        """
        query_lower = query.lower()

        # 总结关键词
        if any(k in query_lower for k in ["总结", "概述", "简要", "快速了解"]):
            return "summary"

        # 分析关键词
        if any(k in query_lower for k in [
            "分析", "对比", "为什么", "怎么样", "预测",
            "谁会赢", "谁更强", "状态"
        ]):
            return "analysis"

        # 默认为查询
        return "query"

    def _extract_entities(self, query: str) -> Dict:
        """
        简单的实体提取（基于映射库）
        """
        entities = {}

        # 球队映射库
        team_map = {
            "曼联": "Manchester United",
            "利物浦": "Liverpool",
            "阿森纳": "Arsenal",
            "曼城": "Manchester City",
            "切尔西": "Chelsea",
            # ... 更多球队
        }

        # 提取球队
        for cn_name, en_name in team_map.items():
            if cn_name in query:
                if 'team' not in entities:
                    entities['team'] = en_name
                    entities['team_a'] = en_name
                else:
                    entities['team_b'] = en_name

        # 联赛映射
        league_map = {
            "英超": "Premier League",
            "西甲": "La Liga",
            "意甲": "Serie A",
            "德甲": "Bundesliga",
        }

        for cn_name, en_name in league_map.items():
            if cn_name in query:
                entities['league'] = en_name

        return entities
```

---

## 四、2周实施计划（简化版）

### Week 1: 基础设施 + 查询模块

#### Day 1-2: 环境搭建
- [x] 部署Ollama + Qwen2.5:7b
- [ ] 修改llm_client.py（支持Ollama）
- [ ] 测试本地模型调用
- [ ] 验证速度和效果

#### Day 3-4: 赛事查询模块
- [ ] 实现MatchQueryModule
  - 战绩查询
  - 排名查询
  - 历史交锋查询
- [ ] LLM格式化输出
- [ ] 单元测试

#### Day 5-7: 测试优化
- [ ] 端到端测试
- [ ] 优化prompt
- [ ] 性能调优

### Week 2: 分析 + 总结模块

#### Day 8-10: 赛事分析模块
- [ ] 实现MatchAnalysisModule
  - 集成DataAnalyzer
  - 集成ReasoningEngine
- [ ] 球队状态分析
- [ ] 两队对比分析
- [ ] 预测分析

#### Day 11-12: 赛事总结模块
- [ ] 实现MatchSummaryModule
- [ ] 比赛总结
- [ ] 球队阶段总结
- [ ] 联赛概况总结

#### Day 13-14: 集成测试
- [ ] SimpleAgent集成
- [ ] 完整流程测试
- [ ] 用户测试（邀请5-10人）
- [ ] 快速迭代优化

---

## 五、关键决策

### 1. 本地模型优先
✅ **Ollama + Qwen2.5:7b**
- 完全免费
- 速度快（1-2秒）
- 中文效果好
- 降级方案：DeepSeek API

### 2. 架构极简化
✅ **只做3个模块**
- 查询、分析、总结
- 不做推荐、不做资讯（暂时）
- 2周内可完成

### 3. 复用已有组件
✅ **复用核心组件**
- DataAnalyzer（数据分析）
- ReasoningEngine（推理引擎）
- 所有现有工具（Match、Stats、Standings）

### 4. 规则优先
✅ **简单规则 + LLM**
- 意图识别：简单关键词匹配
- 实体提取：映射库
- LLM只负责生成和美化输出

---

## 六、预期效果

### 功能覆盖
- ✅ 查询球队战绩、排名
- ✅ 深度分析球队状态
- ✅ 两队对比分析
- ✅ 比赛预测分析
- ✅ 简洁的总结摘要

### 性能指标
- 响应时间: 1-2秒
- 准确率: >80%（意图识别）
- 用户满意度: >4.0/5.0

### 成本
- API费用: ¥0（本地模型）
- 开发时间: 2周
- 维护成本: 低

---

## 总结

这个简化版架构：

1. ✅ **聚焦核心价值** - 只做最重要的3个模块
2. ✅ **本地模型优先** - 降低成本，提升速度
3. ✅ **复用已有组件** - DataAnalyzer、ReasoningEngine
4. ✅ **规则优先** - 简单可控，快速上线
5. ✅ **2周可完成** - 实际可执行的计划

**下一步**：立即开始Day 1-2任务（部署本地模型）
