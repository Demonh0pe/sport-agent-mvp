# Agent 设计文档（MVP v1.0）

## 目标
- 支撑“预测 + 资讯 + 策略”多轮问答。
- 可扩展多工具、可追溯调用轨迹、可插拔模型。

## 能力分层
1. **Planner（意图理解）**：ReAct + 规则模板判断需调用的工具序列。
2. **Executor（工具编排）**：按步骤调用 PredictionTool、NewsTool、OddsTool、StrategyTool，可串行/并行。
3. **Memory**：
   - 短期：会话上下文（Redis）。
   - 长期：用户画像、偏好（PostgreSQL / PgVector）。
4. **Reasoner/LLM**：将工具结果转化为自然语言回答并生成解释。
5. **Guardrail**：敏感词过滤、事实校验、调用上限控制。

## 功能域与分析方向
- **比赛分析解读**  
  - `1.1` 统计：球队/球员基本面、近期状态、体能密度。  
  - `1.2` 历史对比：H2H、主客场差异、关键球员对比。  
  - `1.3` 战术：阵型、风格、教练调整。  
  - `1.4` 实时：赛中核心指标偏差、事件提醒。  
  - `1.5` 赛后复盘：事件时间线、预测 vs 结果回看。
- **比赛预测**  
  - `2.1` 胜平负：ML + Elo。  
  - `2.2` 比分：Poisson/区间预测。  
  - `2.3` 特殊事件：进球数、角球、牌数等。  
  - `2.4` LLM 增强：新闻/舆论/多模态融合、CoT 推理。

## 工具清单（扩展）
| 工具 | 功能 | 输入 | 输出 |
| --- | --- | --- | --- |
| MatchResolverTool | NLP 解析自然语言 → `match_id` | 文本查询 | `match_id`, `meta` |
| StatsAnalysisTool | 球队/球员统计解读 (1.1) | `match_id`, `scope` | 指标聚合、亮点与隐患 |
| HistoricalComparisonTool | H2H & 主客场对比 (1.2) | `match_id`, `window` | 历史胜率、主客差异、关键球员对比 |
| TacticalInsightTool | 阵型/战术洞察 (1.3) | `match_id` | 战术风格、阵型趋势、教练策略 |
| LiveFeedTool | 赛中实时指标 (1.4) | `match_id` | 实时控球/射门/事件，偏差提醒 |
| PostMatchReviewTool | 赛后复盘 (1.5) | `match_id` | 事件时间线、关键因子回顾 |
| PredictionTool | 胜平负概率 + 解释 (2.1) | `match_id`, `phase` | 概率、解释、置信度 |
| ScorelinePredictorTool | 比分/区间预测 (2.2) | `match_id` | 最可能比分、区间概率 |
| EventPredictorTool | 进球数/角球/牌等 (2.3) | `match_id`, `event_type` | 事件概率、触发条件 |
| NewsTool | 最新资讯/伤停摘要 | `entity_id`, `window_hours` | 资讯列表（情绪、可信度） |
| OddsTool | 市场盘口对比 | `match_id` | 最新赔率、异常提示 |
| LLMAugmentorTool | LLM 结合定性信息生成 CoT 解释 (2.4) | `context`, `features` | 推理链、文本解释 |
| StrategyTool | 风险策略建议 | `preference`, `context` | 推荐策略 + 理由 |

> 工具定义位于 `config/agent_tools.yaml`，Agent Service 通过 HTTP/内部 RPC 调用，可按需开启/禁用。

## 流程示例
```
用户提问 → Planner 识别为「预测 + 资讯」→
  调 PredictionTool(match_id) → 得到概率/解释
  调 NewsTool(match_id) → 得到最新资讯
→ Reasoner 结合结果生成答案 + Trace
→ Guardrail 检查 → 返回
```

## 数据结构
- `AgentQuery` / `AgentResponse` / `ToolInvocation`（见 `src/services/api/schemas/agent.py`）。
- `conversation_trace`：记录工具调用顺序、耗时、输入输出摘要供事后审计。

## 扩展规划
- 引入 `MatchResolverTool`（NLP → match_id），减少用户输入结构化负担。
- 增加多模态工具（视频集锦/战术板）。
- 接入推荐系统，支持“订阅 + Push”场景。
- 可配置 LLM 通道（OpenAI / Azure / 本地）与提示模板版本。
