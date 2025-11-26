# 数据层与意图体系设计指南

版本：v2.0
更新日期：2025-11-26

---

## 概览

本文档定义了Sport Agent系统的数据层和意图识别体系，是零硬编码架构的核心指南。

---

## 数据层架构

### 1. 实体解析（EntityResolver）

#### 核心职责
- 将用户输入（中英文、缩写）映射到标准实体ID
- 从数据库动态加载所有别名
- 支持模糊匹配和搜索建议
- 零硬编码

#### 实现位置
`src/data_pipeline/entity_resolver.py`

#### 关键方法
```python
class EntityResolver:
    async def resolve_team(self, name: str) -> Optional[str]
    async def resolve_league(self, code: str) -> Optional[str]
    async def search_teams(self, query: str, limit: int) -> List[Dict]
    async def search_leagues(self, query: str, limit: int) -> List[Dict]
```

---

## 意图体系

### 支持的意图类型

| 意图 | 说明 | 示例 |
|------|------|------|
| query | 查询事实信息 | "曼联最近5场战绩" |
| prediction | 预测比赛结果 | "曼联对利物浦谁会赢" |
| comparison | 对比两队实力 | "曼联和利物浦谁更强" |
| analysis | 分析状态趋势 | "分析曼联最近状态" |
| summary | 总结概况 | "总结切尔西本赛季" |
| clarification | 澄清不明确查询 | "球队怎么样" |

### 意图分类器（IntentClassifier）

#### 实现位置
`src/agent/core/intent_classifier.py`

#### 双引擎策略

**引擎1：规则匹配**（优先）
- 速度：< 1ms
- 准确率：85%
- 成本：免费
- 适用：常见查询

**引擎2：LLM分类**（兜底）
- 速度：1-2秒
- 准确率：90%+
- 成本：低
- 适用：复杂/模糊查询

#### 工作流程
```
用户查询
    ↓
规则匹配（关键词）
    ↓
置信度 >= 0.7？
    ├─ 是：返回结果
    └─ 否：LLM分类
        ↓
    返回最终结果
```

---

## 场景处理器

### 1. 对比场景（ComparisonScenario）

#### 触发条件
- 意图为 comparison
- 提取到2个球队实体

#### 处理流程
1. 解析两支球队
2. 获取历史交锋（H2H）
3. 获取统计数据
4. 生成对比报告

#### 实现位置
`src/agent/scenarios/comparison_scenario.py`

### 2. 澄清场景（ClarificationScenario）

#### 触发条件
- 意图为 clarification
- 或实体提取失败
- 或意图识别置信度低

#### 澄清类型
1. missing_team - 缺少球队信息
2. missing_league - 缺少联赛信息
3. ambiguous_team - 球队名称模糊
4. intent_unclear - 意图不明确
5. insufficient_info - 信息不足

#### 实现位置
`src/agent/scenarios/clarification_scenario.py`

---

## 数据访问工具

### MatchTool
**文件**：`src/agent/tools/match_tool.py`

**方法**：
- `get_recent_matches(team, limit)` - 查询最近比赛
- `get_head_to_head_matches(team_a, team_b, limit)` - 历史交锋

### StandingsTool
**文件**：`src/agent/tools/standings_tool.py`

**方法**：
- `get_team_standing(team_id, league_id)` - 查询排名
- `get_league_standings(league_id, limit)` - 联赛积分榜

### StatsTool
**文件**：`src/agent/tools/stats_tool.py`

**方法**：
- `get_team_stats(team_id)` - 球队统计
- `calculate_form(team_id, n_matches)` - 计算状态

### PredictionTool
**文件**：`src/agent/tools/prediction_tool.py`

**方法**：
- `predict_match(home_team, away_team)` - 预测比赛
- `get_win_probability(team_a, team_b)` - 获取胜率

---

## 中英文处理

### TranslationHelper

#### 三层机制

**层1：预定义术语**（最快）
- 50+常用足球术语
- 响应时间：< 1ms
- 准确率：100%

**层2：缓存结果**（较快）
- 自动缓存LLM翻译
- 响应时间：< 50ms
- 命中率：60%+

**层3：LLM翻译**（最灵活）
- 处理新术语
- 响应时间：1-3秒
- 准确率：95%

#### 实现位置
`src/shared/translation_helper.py`

---

## 数据流向

```
用户输入（中英文）
    ↓
IntentClassifier（识别意图）
    ↓
EntityResolver（提取实体）
    ↓
场景路由
    ├─ QueryModule
    ├─ AnalysisModule
    ├─ SummaryModule
    ├─ ComparisonScenario
    └─ ClarificationScenario
    ↓
数据访问工具
    ├─ MatchTool
    ├─ StandingsTool
    ├─ StatsTool
    └─ PredictionTool
    ↓
TranslationHelper（翻译展示）
    ↓
LLM生成自然语言回复
    ↓
返回给用户（中文为主）
```

---

## 设计原则

1. **零硬编码**：所有实体从数据库加载
2. **异步优先**：所有I/O操作异步
3. **模块化**：高内聚低耦合
4. **可扩展**：易于添加新意图、新工具
5. **容错性**：优雅降级，不崩溃

---

## 扩展指南

### 添加新意图

1. 在 `IntentClassifier` 添加规则
2. 创建对应的场景处理器
3. 在 `SimpleAgentV2` 添加路由

### 添加新工具

1. 在 `src/agent/tools/` 创建新工具
2. 定义工具Schema
3. 在场景处理器中调用

### 添加新数据源

1. 在 `src/data_pipeline/` 创建ingester
2. 实现异步数据拉取
3. 对齐实体到标准ID
4. 打标签并入库

---

参考文档：
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) - 详细架构
- [ZERO_HARDCODE_IMPLEMENTATION.md](ZERO_HARDCODE_IMPLEMENTATION.md) - 实施细节

