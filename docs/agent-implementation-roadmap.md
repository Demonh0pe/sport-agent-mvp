# Sport Agent 企业级实施路线图

**文档状态**: Agent Phase 1 规划（Week 1-2）
**最后更新**: 2024-11-21
**负责人**: Agent Team (你)

---

## 📊 当前状态快照

### ✅ 已完成 (Week 0)
- [x] Planner v1.2: 100% 通过 Golden Dataset
- [x] 12 种工具接口完整定义
- [x] API 框架与路由
- [x] 工具注册表配置

### 🚀 刚完成 (Today)
- [x] ParameterResolver - 参数解析与绑定系统
- [x] Executor - 工具执行框架
- [x] MockToolResponses - 完整 Mock 数据库 (13 种工具)
- [x] AgentOrchestrator - 编排器整合

### ⏳ 下一步 (Week 1-2)
- [ ] 集成到 API 服务
- [ ] 端到端测试
- [ ] 性能基线建立
- [ ] 文档与演示

---

## 🎯 Phase 1: 核心执行层 (Week 1-2)

### 任务 1.1: 参数解析与绑定系统 ✅ 完成

**文件**: `src/agent/core/parameter_resolver.py` (220 行)

**核心功能**:
```python
# 输入
step = "PredictionTool(match_id=$match_id, phase='T-24h')"

# 解析
parsed = resolver.parse_step(step)
# 输出: ParsedToolStep(
#   tool_name="PredictionTool",
#   raw_params={"match_id": "$match_id", "phase": "'T-24h'"},
# )

# 填充占位符
context = {"match_id": "man-utd-001"}
resolved = resolver.resolve_placeholders(parsed, context)
# 输出: params = {"match_id": "man-utd-001", "phase": "T-24h"}
```

**关键能力**:
- ✅ 工具步骤字符串正则解析
- ✅ 参数提取与分割
- ✅ 占位符识别与绑定
- ✅ 类型转换 (字符串/数字/布尔/数组)
- ✅ 错误处理

**代码示例**:
```python
from src.agent.core.parameter_resolver import ParameterResolver

resolver = ParameterResolver()

# 1. 解析
parsed = resolver.parse_step("MatchResolverTool(query='Barcelona')")
# ParsedToolStep(tool_name="MatchResolverTool", raw_params={"query": "Barcelona"})

# 2. 填充占位符
context = {"match_id": "barcelona-001"}
resolved = resolver.resolve_placeholders(parsed, context)
# params = {"query": "Barcelona"}

# 3. 批量处理
all_resolved = resolver.resolve_all_steps(plan_steps)
```

---

### 任务 1.2: Executor 工具执行框架 ✅ 完成

**文件**: `src/agent/core/executor.py` (310 行)

**核心功能**:
```python
async with Executor(settings) as executor:
    result = await executor.execute_plan(
        plan_steps=[
            "MatchResolverTool(query='Barcelona')",
            "PredictionTool(match_id=$match_id, phase='T-24h')",
        ],
        match_id_hint="barca-001"  # 可选初始化
    )
```

**工作流**:
```
输入: plan_steps
  ↓
参数解析 (ParameterResolver)
  ↓
遍历每个步骤:
  - 查询工具配置
  - 构建 HTTP 请求
  - 发送请求 (httpx)
  - 解析响应
  - 更新上下文
  ↓
返回: execution_summary
```

**关键特性**:
- ✅ 工具查询与配置映射
- ✅ HTTP 客户端管理 (httpx AsyncClient)
- ✅ 请求/响应处理
- ✅ 上下文维护与更新
- ✅ 错误处理与日志
- ✅ 性能追踪 (latency_ms)

**设计优势**:
- 异步执行 (asyncio)
- 参数依赖自动填充
- 超时控制
- 失败恢复

---

### 任务 1.3: Mock 工具响应库 ✅ 完成

**文件**: `src/agent/tools/mock_responses.py` (650 行)

**包含 13 种工具的完整 Mock 实现**:

| 工具 | 响应类型 | 数据量 | 覆盖场景 |
|------|---------|--------|---------|
| MatchResolverTool | match_id, teams | 5 对球队 | 足球、非足球 |
| StatsAnalysisTool | highlights, flags | 4-6 项 | 强队、弱队、伤病 |
| HistoricalComparisonTool | h2h_summary, advantage | 文本 + 浮点 | 势均力敌、单边压倒 |
| TacticalInsightTool | formations, style | 列表 + Literal | 5 种战术风格 |
| LiveFeedTool | possession, events | 实时数据 | 领先、落后、平局 |
| PostMatchReviewTool | timeline, comparison | 长文本 | 各种结局 |
| **PredictionTool** | home/draw/away | 概率分布 | 冷门、热门 |
| ScorelinePredictorTool | scorelines, probs | top-3 | 常见比分 |
| EventPredictorTool | buckets, probs | 3-4 档 | 进球、角球、黄牌 |
| NewsTool | items, summary | 3 条新闻 | 伤病、转会、战术 |
| OddsTool | markets, anomalies | 2 家博彩 | 正常、异常波动 |
| LLMAugmentorTool | reasoning_chain | CoT 步骤 | 推理链 |
| StrategyTool | recommendation | 3 种偏好 | 保守、均衡、激进 |

**关键特性**:
- ✅ 确定性伪数据 (基于 hash seed)
- ✅ 高度真实性 (分布符合足球比赛)
- ✅ 覆盖各种场景 (无缝集成到测试)
- ✅ Pydantic Schema 验证
- ✅ 易于逐步替换为真实服务

**使用示例**:
```python
from src.agent.tools.mock_responses import MockToolResponses

mock = MockToolResponses()

# 确定性伪数据
pred1 = mock.prediction(match_id="barca-001", phase="T-24h")
pred2 = mock.prediction(match_id="barca-001", phase="T-24h")
# pred1 == pred2 (完全相同，便于调试)

# 不同的 match_id → 不同的预测
pred3 = mock.prediction(match_id="real-001", phase="T-24h")
# pred3 != pred1 (完全不同)
```

---

### 任务 1.4: Agent 编排器 ✅ 完成

**文件**: `src/agent/orchestrator.py` (280 行)

**整合 Planner + Executor + Mock**:
```python
orchestrator = AgentOrchestrator(settings)

result = await orchestrator.orchestrate(
    query="巴萨下一场谁会赢？",
    user_id="user_123",
    preferred_phase="T-24h",
)

# 输出:
{
    "query": "巴萨下一场谁会赢？",
    "plan_steps": [
        "MatchResolverTool(query='...Barcelona...')",
        "PredictionTool(match_id=$match_id, phase='T-24h')",
        ...
    ],
    "execution_result": {
        "tools_executed": ["MatchResolverTool", "PredictionTool"],
        "results": {
            "MatchResolverTool": {...},
            "PredictionTool": {...},
        },
        "total_latency_ms": 250
    },
    "answer": "我已经为您的问题... [详细分析]",
    "status": "success"
}
```

**工作流**:
```
用户查询
  ↓
Planner.plan_decomposition()
  ↓
Executor.execute_plan() (当前: Mock)
  ↓
_build_answer() (自然语言整合)
  ↓
返回完整响应
```

---

## 📋 下一步: Phase 1 完成清单 (Week 1)

### 任务 1.5: 集成到 API 服务

**当前状态**: AgentService 仍使用旧的 Mock 逻辑

**需要做**:
```python
# 文件: src/services/api/services/agent.py (更新)

class AgentService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self.orchestrator = AgentOrchestrator(settings)  # 新增

    async def run_query(self, payload: AgentQuery) -> AgentResponse:
        # 使用新的 Orchestrator
        result = await self.orchestrator.orchestrate(
            query=payload.query,
            user_id=payload.user_id,
            preferred_phase=payload.preferred_phase,
        )

        # 转换为 API 响应格式
        return AgentResponse(
            answer=result["answer"],
            reasoning=self._extract_reasoning(result),
            plan_steps=result["plan_steps"],
            tool_traces=self._build_traces(result["execution_result"]),
            planner_version="v1.2+executor",
            generated_at=datetime.now(timezone.utc),
        )
```

**工时**: 2-3 小时

---

### 任务 1.6: 端到端测试

**创建测试文件**: `tests/test_agent_e2e.py`

```python
import pytest
from src.services.api.services.agent import AgentService
from src.services.api.schemas.agent import AgentQuery
from src.shared.config import get_settings

@pytest.mark.asyncio
async def test_agent_e2e_basic():
    """测试: Agent 完整流程"""
    settings = get_settings()
    service = AgentService(settings)

    payload = AgentQuery(query="巴萨下一场谁会赢？")
    response = await service.run_query(payload)

    # 验证响应结构
    assert response.answer is not None
    assert len(response.plan_steps) > 0
    assert response.planner_version == "v1.2+executor"

@pytest.mark.asyncio
async def test_agent_multi_tool():
    """测试: 多工具协作"""
    settings = get_settings()
    service = AgentService(settings)

    # 复杂查询: 需要多个工具
    payload = AgentQuery(
        query="巴黎这波连胜能否持续？请结合赛程和体能。"
    )
    response = await service.run_query(payload)

    # 验证多个工具被调用
    assert len(response.plan_steps) >= 3
    assert any("Stats" in step for step in response.plan_steps)
    assert any("News" in step for step in response.plan_steps)

@pytest.mark.asyncio
async def test_golden_dataset():
    """回归测试: Golden Dataset 所有 20 个用例"""
    import json
    settings = get_settings()
    service = AgentService(settings)

    with open("tests/data/golden_dataset.json") as f:
        dataset = json.load(f)

    for case in dataset:
        payload = AgentQuery(query=case["question"])
        response = await service.run_query(payload)

        # 验证响应有效
        assert response.answer is not None
        assert len(response.plan_steps) > 0
```

**工时**: 4-6 小时

---

### 任务 1.7: 性能基线建立

**创建性能测试**: `tests/test_agent_performance.py`

```python
import asyncio
import time
import pytest
from src.services.api.services.agent import AgentService
from src.services.api.schemas.agent import AgentQuery
from src.shared.config import get_settings

@pytest.mark.asyncio
async def test_agent_latency():
    """性能基线: 单次查询延迟"""
    settings = get_settings()
    service = AgentService(settings)

    queries = [
        "巴萨下一场谁会赢？",
        "曼联和利物浦最近5次交锋谁更强？",
        "巴黎这波连胜能否持续？",
    ]

    latencies = []
    for query in queries:
        payload = AgentQuery(query=query)

        start = time.time()
        response = await service.run_query(payload)
        latency = (time.time() - start) * 1000  # ms

        latencies.append(latency)

    print(f"✅ 性能基线:")
    print(f"   平均延迟: {sum(latencies)/len(latencies):.0f} ms")
    print(f"   最小延迟: {min(latencies):.0f} ms")
    print(f"   最大延迟: {max(latencies):.0f} ms")

    # 约束: 单次查询 < 1000 ms (当前 Mock, 应该 < 500ms)
    assert sum(latencies) / len(latencies) < 1000

@pytest.mark.asyncio
async def test_concurrent_queries():
    """压力测试: 并发查询"""
    settings = get_settings()
    service = AgentService(settings)

    async def query():
        payload = AgentQuery(query="巴萨下一场谁会赢？")
        return await service.run_query(payload)

    # 10 个并发查询
    start = time.time()
    results = await asyncio.gather(*[query() for _ in range(10)])
    total_time = time.time() - start

    print(f"✅ 并发性能:")
    print(f"   10 个查询耗时: {total_time*1000:.0f} ms")
    print(f"   平均每个: {total_time*1000/10:.0f} ms")

    assert len(results) == 10
    assert all(r.answer is not None for r in results)
```

**工时**: 3-4 小时

---

### 任务 1.8: 文档与演示

**更新文档**:
- `docs/agent-implementation-roadmap.md` (本文档)
- `docs/agent-api-usage.md` (API 使用指南)
- `src/agent/orchestrator.py` (代码注释)

**创建演示脚本**: `demo_agent.py`

```python
#!/usr/bin/env python3
"""Agent 演示脚本"""
import asyncio
from src.services.api.services.agent import AgentService
from src.services.api.schemas.agent import AgentQuery
from src.shared.config import get_settings

async def main():
    settings = get_settings()
    service = AgentService(settings)

    # 演示 1: 简单预测
    print("\n[演示 1] 简单预测")
    print("=" * 50)
    payload = AgentQuery(query="巴萨下一场谁会赢？")
    response = await service.run_query(payload)
    print(f"用户提问: {payload.query}")
    print(f"Agent 回答: {response.answer[:200]}...")
    print(f"使用工具: {response.plan_steps}")

    # 演示 2: 复杂分析
    print("\n[演示 2] 复杂分析")
    print("=" * 50)
    payload = AgentQuery(
        query="巴黎这波连胜是否可持续？请结合赛程和体能。"
    )
    response = await service.run_query(payload)
    print(f"用户提问: {payload.query}")
    print(f"Agent 回答: {response.answer[:200]}...")
    print(f"使用工具数: {len(response.plan_steps)}")

    # 演示 3: 多轮对话示意
    print("\n[演示 3] 多工具协作")
    print("=" * 50)
    print(f"用户提问: 马德里德比赔率有没有异常波动？")
    payload = AgentQuery(query="马德里德比赔率有没有异常波动？")
    response = await service.run_query(payload)
    print(f"使用工具: {response.plan_steps}")

if __name__ == "__main__":
    asyncio.run(main())
```

**工时**: 2-3 小时

---

## 🎯 Phase 2: 优化与扩展 (Week 2-3)

### 可选任务 2.1: Multi-Turn 对话

**目标**: 支持追问与上下文传递

```python
# API 支持对话历史
POST /api/v1/agent/query
{
    "conversation_id": "conv_123",  # 新增
    "query": "为什么？",
    "user_id": "user_456"
}

Response:
{
    "answer": "因为主队伤病较多...",
    "context": {  # 新增
        "previous_query": "巴萨下一场谁会赢？",
        "conversation_history": [...]
    }
}
```

**实现方案**:
- Redis 存储对话 context (TTL=1 hour)
- Context Compression (窗口超限时摘要)
- 自动 query 补全

---

### 可选任务 2.2: LLM 集成

**目标**: 用真实 LLM 生成自然语言

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

response = await client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "system",
            "content": "你是一名资深足球评论员..."
        },
        {
            "role": "user",
            "content": f"根据以下分析结果回答: {tool_outputs}"
        }
    ],
    temperature=0.7,
    max_tokens=500,
)
```

---

### 可选任务 2.3: 缓存系统

**目标**: 加速重复查询

```python
# Redis 缓存策略
cache_key = f"tool:{tool_name}:{hash(params)}"
cached = await redis.get(cache_key)

if cached:
    return json.loads(cached)  # 命中缓存

# 执行工具
result = await executor.execute_tool(...)

# 写入缓存 (TTL=5 min)
await redis.setex(cache_key, 300, json.dumps(result))
```

---

## 📊 交付清单

### Week 1 完成标准
- [x] ParameterResolver 完整实现
- [x] Executor 框架就位
- [x] MockToolResponses 13 种工具覆盖
- [x] AgentOrchestrator 整合
- [ ] 集成到 AgentService
- [ ] 端到端测试覆盖 (Golden Dataset)
- [ ] 性能基线确立 (P50 < 500ms, P99 < 1000ms)
- [ ] API 文档更新

### 成功指标
- **功能**: Golden Dataset 100% 通过
- **性能**: 单次查询 < 1000ms
- **可靠性**: 并发 10 个查询无错误
- **覆盖**: 13 种工具全部可用

---

## 🔄 与其他模块的集成

### 与 Prediction Service 的集成
```
Agent Query
  → PredictionTool 调用
  → src/services/api/services/prediction.py
  → 当前返回 Mock 数据
  → 未来: 真实 XGBoost 模型
```

### 与 News Service 的集成
```
Agent Query
  → NewsTool 调用
  → src/services/api/services/news.py
  → 当前返回 Mock 数据
  → 未来: 真实资讯爬虫 + NLP
```

---

## 📚 参考文档

- `docs/agent-design.md` - Agent 架构设计
- `docs/project-initial-plan.md` - 项目整体计划
- `config/agent_tools.yaml` - 工具注册表
- `tests/data/golden_dataset.json` - 20 个测试用例

---

## ⚡ 快速启动

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 运行 Planner 回归测试
python3 evaluate_planner.py --verbose

# 3. 启动 API 服务
uvicorn src.services.api.main:app --reload

# 4. 在另一个终端测试
curl -X POST http://localhost:8080/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "巴萨下一场谁会赢？"}'

# 5. 查看 Swagger 文档
# 访问 http://localhost:8080/docs
```

---

## 💬 常见问题

### Q: 为什么使用 Mock 工具？
**A**: 在真实数据源（特征仓、模型服务、资讯爬虫）就位前，Mock 提供：
- 不被数据延迟阻塞
- 快速的功能验证
- 清晰的工具接口
- 逐步替换的通道

### Q: 何时用真实数据替换 Mock？
**A**: 当以下模块完成时：
1. Prediction Service - 真实 XGBoost 模型
2. News Service - 资讯爬虫与 NLP
3. Feature Store - 球队/球员特征
4. Entity Resolution - 球队/球员映射

### Q: Agent 性能瓶颈在哪？
**A**: 当前（Mock）: 网络 I/O（Executor）
未来（真实）: Model inference (PredictionTool), 资讯查询 (NewsTool)

---

**下一步**: 选择 Phase 1.5 或 Phase 2 中的任务开始实施！
