# 🤖 Sport Agent 快速开始指南

## 文件结构导图

```
src/agent/
├── core/
│   ├── planner.py              ✅ Planner (意图识别 + 工具链规划)
│   ├── executor.py             ✅ NEW - Executor (工具执行)
│   └── parameter_resolver.py   ✅ NEW - 参数解析与绑定
├── tools/
│   ├── schemas.py              ✅ 13 种工具的 I/O 定义
│   └── mock_responses.py       ✅ NEW - Mock 工具数据库
└── orchestrator.py             ✅ NEW - 编排器 (整合 Planner+Executor)

src/services/api/
├── services/
│   ├── agent.py                🟡 需要更新 (集成新的 Orchestrator)
│   ├── prediction.py
│   └── news.py
├── schemas/agent.py
└── routers/agent.py

tests/
├── data/
│   └── golden_dataset.json     ✅ 20 个测试用例
└── test_agent_e2e.py           📝 待创建
```

---

## 新增关键类

### 1. ParameterResolver
**文件**: `src/agent/core/parameter_resolver.py`

```python
from src.agent.core.parameter_resolver import ParameterResolver

resolver = ParameterResolver()

# 解析工具步骤字符串
parsed = resolver.parse_step("PredictionTool(match_id=$match_id, phase='T-24h')")

# 填充占位符
context = {"match_id": "barca-001"}
resolved = resolver.resolve_placeholders(parsed, context)
print(resolved.params)  # {'match_id': 'barca-001', 'phase': 'T-24h'}

# 批量处理（自动处理依赖）
all_steps = resolver.resolve_all_steps(plan_steps)
```

**关键方法**:
- `parse_step(step: str) -> ParsedToolStep` - 解析单个步骤
- `resolve_placeholders(parsed, context) -> ParsedToolStep` - 填充占位符
- `resolve_all_steps(steps) -> List[ParsedToolStep]` - 批量处理

---

### 2. Executor
**文件**: `src/agent/core/executor.py`

```python
from src.agent.core.executor import Executor

async with Executor(settings) as executor:
    result = await executor.execute_plan(
        plan_steps=[
            "MatchResolverTool(query='Barcelona')",
            "PredictionTool(match_id=$match_id, phase='T-24h')",
        ]
    )

print(result)
# {
#     "status": "completed",
#     "execution_stats": {
#         "total_tools": 2,
#         "successful": 2,
#         "failed": 0,
#         "total_latency_ms": 250
#     },
#     "results": [
#         {"tool": "MatchResolverTool", "output": {...}},
#         {"tool": "PredictionTool", "output": {...}},
#     ],
#     "context": {"match_id": "barca-001", ...}
# }
```

**关键方法**:
- `async execute_plan(steps, match_id_hint) -> Dict` - 执行完整工具链
- 自动处理参数依赖
- HTTP 请求管理与超时控制

---

### 3. MockToolResponses
**文件**: `src/agent/tools/mock_responses.py`

```python
from src.agent.tools.mock_responses import MockToolResponses

mock = MockToolResponses()

# 各种工具的 Mock 响应
pred = mock.prediction(match_id="barca-001")
# PredictionToolOutput(
#     model_version="xgb_v2.1",
#     home_win=0.45,
#     draw=0.28,
#     away_win=0.27,
#     ...
# )

news = mock.news(entity_id="Barcelona", window_hours=72)
# NewsToolOutput(
#     items=[...],
#     summary_of_consensus="..."
# )

# 确定性: 相同输入 → 相同输出
pred1 = mock.prediction("barca-001")
pred2 = mock.prediction("barca-001")
assert pred1 == pred2  # True
```

**13 种工具方法**:
```python
mock.match_resolver(query, league_hint, date_hint)
mock.stats_analysis(match_id, scope, window)
mock.historical_comparison(match_id, window)
mock.tactical_insight(match_id)
mock.live_feed(match_id)
mock.post_match_review(match_id)
mock.prediction(match_id, phase)
mock.scoreline_predictor(match_id)
mock.event_predictor(match_id, event_type)
mock.news(entity_id, entity_type, window_hours)
mock.odds(match_id)
mock.llm_augmentor(context, evidence)
mock.strategy(preference, context)
```

---

### 4. AgentOrchestrator
**文件**: `src/agent/orchestrator.py`

```python
from src.agent.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator(settings)

result = await orchestrator.orchestrate(
    query="巴萨下一场谁会赢？",
    user_id="user_123",
    preferred_phase="T-24h",
)

print(result)
# {
#     "query": "巴萨下一场谁会赢？",
#     "plan_steps": [...],
#     "execution_result": {...},
#     "answer": "我已经为您... [完整分析]",
#     "status": "success"
# }
```

**工作流**:
1. 调用 Planner 生成工具链
2. 调用 Executor 执行工具（当前使用 Mock）
3. 自动生成自然语言答案

---

## 使用示例

### 示例 1: 完整的 Agent 流程

```python
import asyncio
from src.agent.orchestrator import AgentOrchestrator
from src.shared.config import get_settings

async def main():
    settings = get_settings()
    orchestrator = AgentOrchestrator(settings)

    # 用户查询
    query = "曼联和利物浦最近5次交锋哪支更占优势？"

    # Agent 执行
    result = await orchestrator.orchestrate(
        query=query,
        user_id="user_001",
    )

    # 输出结果
    print(f"用户提问: {result['query']}")
    print(f"\nPlanner 生成的工具链:")
    for step in result['plan_steps']:
        print(f"  - {step}")

    print(f"\nAgent 回答:")
    print(f"  {result['answer']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 2: 参数解析与绑定

```python
from src.agent.core.parameter_resolver import ParameterResolver

resolver = ParameterResolver()

# Planner 输出的工具链
steps = [
    "MatchResolverTool(query='Manchester United vs Liverpool')",
    "HistoricalComparisonTool(match_id=$match_id, window=5)",
]

# 逐步解析与绑定
for step in steps:
    parsed = resolver.parse_step(step)
    print(f"✅ 解析: {parsed.tool_name}")
    print(f"   参数: {parsed.raw_params}")

# 模拟执行流
context = {}
for step in steps:
    parsed = resolver.parse_step(step)

    # 如果有占位符，填充
    if any(v.startswith("$") for v in parsed.raw_params.values()):
        parsed = resolver.resolve_placeholders(parsed, context)
        print(f"✅ 填充后: {parsed.params}")

    # 模拟工具执行
    if parsed.tool_name == "MatchResolverTool":
        context["match_id"] = "man-utd-vs-liv-001"
        context["home_team_id"] = "manchester-united"
        context["away_team_id"] = "liverpool"
```

### 示例 3: Mock 工具独立使用

```python
from src.agent.tools.mock_responses import MockToolResponses

mock = MockToolResponses()

# 为 Agent 演示生成各种场景的数据
print("=== 预测结果 ===")
pred = mock.prediction(match_id="barca-001")
print(f"主胜: {pred.home_win:.1%}")
print(f"平局: {pred.draw:.1%}")
print(f"客胜: {pred.away_win:.1%}")

print("\n=== 历史对比 ===")
hist = mock.historical_comparison(match_id="barca-001", window=5)
print(f"H2H: {hist.h2h_summary}")
print(f"主场优势: {hist.home_home_advantage:.1%}")

print("\n=== 新闻资讯 ===")
news = mock.news(entity_id="Barcelona")
for item in news.items:
    print(f"  - {item.title}")
```

---

## 快速测试

### 1. 运行 Planner 回归测试

```bash
cd /Users/dylan/Desktop/sport\ agent\ mvp
python3 evaluate_planner.py --verbose
```

**预期输出**:
```
PASS Q1 | 巴萨下一场对手是谁？能给一份胜平负概率吗？
PASS Q2 | C罗这周进球了吗？
...
Passed: 20/20 | Score: 100.0/100
```

---

### 2. 启动 API 服务

```bash
source .venv/bin/activate
uvicorn src.services.api.main:app --reload --port 8080
```

### 3. 测试 Agent 端点 (当前使用旧 Mock)

```bash
curl -X POST http://localhost:8080/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "巴萨下一场谁会赢？",
    "preferred_phase": "T-24h",
    "strategy_preference": "balanced"
  }'
```

---

## 下一步任务优先级

### 紧急 (Week 1)
1. **集成 Orchestrator 到 AgentService** (2-3 小时)
   - 更新 `src/services/api/services/agent.py`
   - 用 `AgentOrchestrator` 替换旧的 Mock 逻辑

2. **端到端测试** (4-6 小时)
   - 创建 `tests/test_agent_e2e.py`
   - 验证 Golden Dataset 20 个用例

3. **性能基线** (3-4 小时)
   - 创建 `tests/test_agent_performance.py`
   - 建立性能指标 (P50, P99)

### 重要 (Week 2)
4. **文档与演示** (2-3 小时)
   - 更新 API 文档
   - 创建 `demo_agent.py`

5. **可选: Multi-Turn 对话** (1-2 周)
   - Redis 上下文存储
   - 自动 query 补全

---

## 关键配置

### service.yaml 中 Agent 配置
```yaml
agent:
  enable_trace: true        # 是否记录工具调用链
  timeout: 30               # 单个工具超时 (秒)
  max_turns: 6              # 最大对话轮数
  default_model: "gpt-3.5-turbo"  # 未来 LLM 模型
```

### agent_tools.yaml
所有 13 种工具的注册信息：
- 名称、描述
- 端点 URL
- HTTP 方法 (GET/POST)
- 参数列表

---

## 常见问题

**Q: 如何调试参数解析？**
```python
resolver = ParameterResolver()
step = "PredictionTool(match_id=$match_id, phase='T-24h')"
parsed = resolver.parse_step(step)
print(f"工具名: {parsed.tool_name}")
print(f"原始参数: {parsed.raw_params}")

# 填充
context = {"match_id": "barca-001"}
resolved = resolver.resolve_placeholders(parsed, context)
print(f"填充后: {resolved.params}")
```

**Q: Mock 数据如何自定义？**
```python
# Mock 响应基于输入的 hash，完全确定性
# 如需自定义场景，可以：

# 方式 1: 直接调用 Mock (编程方式)
mock = MockToolResponses()
custom_pred = mock.prediction("custom-match-id")

# 方式 2: 扩展 MockToolResponses (未来)
class CustomMockResponses(MockToolResponses):
    def prediction(self, match_id, phase="T-24h"):
        # 自定义逻辑
        pass
```

**Q: 如何切换到真实工具？**

当真实服务就位时（如 PredictionService），修改工具注册表：
```yaml
# config/agent_tools.yaml
- name: PredictionTool
  endpoint: http://localhost:8080/api/v1/prediction  # 改为真实服务
  method: GET
  params: [match_id, phase]
```

Executor 会自动调用真实服务，无需修改 Agent 代码。

---

## 📚 参考资源

- **技术设计**: `docs/sport-agent-tech-design.md`
- **Agent 设计**: `docs/agent-design.md`
- **实施路线图**: `docs/agent-implementation-roadmap.md` (新)
- **项目计划**: `docs/project-initial-plan.md`
- **配置**: `config/agent_tools.yaml`, `config/service.yaml`

---

## 🚀 最后

这个框架已经为企业级生产做好了准备：
- ✅ 清晰的层次划分 (Planner → Executor → Reasoner)
- ✅ 完整的工具接口定义
- ✅ Mock 数据支持快速开发
- ✅ 易于逐步替换为真实服务

**建议**: 先完成集成和测试，然后再考虑 Multi-Turn 和 LLM 集成。
