# Sport Agent MVP 测试指南

## 📋 测试前检查清单

- [ ] PostgreSQL 数据库运行中（localhost:5432）
- [ ] 已执行数据库迁移（`alembic upgrade head`）
- [ ] 已播种测试数据（`python scripts/seed_db.py`）
- [ ] 虚拟环境已激活（`source .venv/bin/activate`）
- [ ] 所有依赖已安装（`pip install -r requirements.txt`）

---

## 🚀 快速开始（5分钟）

### 1. 启动 API 服务

```bash
# 方式 1: 前台运行（推荐用于测试）
uvicorn src.services.api.main:app --reload --port 8080

# 方式 2: 后台运行
uvicorn src.services.api.main:app --reload --port 8080 &

# 验证服务启动
curl http://localhost:8080/health
# 预期输出: {"status":"ok","version":"0.1.0"}
```

### 2. 访问 Swagger 文档

打开浏览器访问：
```
http://localhost:8080/docs
```

您将看到所有 API 端点的交互式文档。

---

## 🧪 模块化测试

### Test 1: 数据管道测试

```bash
# 测试实体对齐、数据摄取、质量监控
python scripts/test_data_pipeline.py
```

**预期输出**：
```
✅ 实体对齐: 6/6 通过
✅ 数据质量监控: 正常运行
⏭️  数据摄取: 跳过（节省 API 配额）
```

---

### Test 2: Agent V1 vs V2 对比测试

```bash
# 测试新旧架构的差异
python scripts/test_agent_v2.py
```

**预期输出**：
```
✅ V1 响应成功 (planner_version: v1.2)
✅ V2 响应成功 (planner_version: v2.0)
✅ V1 vs V2 对比完成
```

---

### Test 3: StatsTool 功能测试

```bash
# 测试球队统计分析功能
python scripts/test_stats_tool.py
```

**预期输出**：
```
✅ 直接调用 StatsTool 成功
✅ 通过 Agent V2 API 调用成功
📊 曼联 vs 利物浦 统计对比完成
```

---

## 🎯 端到端测试

### 场景 1: 查询球队比赛记录

**V1 接口**：
```bash
curl -X POST 'http://localhost:8080/api/v1/agent/query' \
  -H 'Content-Type: application/json' \
  -d '{"query": "曼联最近的比赛情况如何？"}' | python3 -m json.tool
```

**V2 接口**（推荐）：
```bash
curl -X POST 'http://localhost:8080/api/v1/agent/query/v2' \
  -H 'Content-Type: application/json' \
  -d '{"query": "曼联最近的比赛情况如何？"}' | python3 -m json.tool
```

**预期响应**：
```json
{
  "answer": "根据提供的数据，曼联在2025年11月21日对阵利物浦...",
  "planner_version": "v2.0",
  "plan_steps": [
    "MatchResolverTool(query='曼联最近的比赛情况如何？')",
    "LLMAugmentorTool(context=$tool_outputs)"
  ],
  "tool_traces": [
    {
      "tool_name": "MatchResolverTool",
      "latency_ms": 39,
      "output_snippet": "📊 曼联 (MUN) 近 5 场比赛记录..."
    }
  ]
}
```

---

### 场景 2: 球队统计分析

```bash
curl -X POST 'http://localhost:8080/api/v1/agent/query/v2' \
  -H 'Content-Type: application/json' \
  -d '{"query": "分析曼联的最近表现"}' | python3 -m json.tool
```

**预期工具链**：
```
MatchResolverTool → StatsAnalysisTool → LLMAugmentorTool
```

---

### 场景 3: 多球队对比

```bash
curl -X POST 'http://localhost:8080/api/v1/agent/query/v2' \
  -H 'Content-Type: application/json' \
  -d '{"query": "对比曼联和利物浦的表现"}' | python3 -m json.tool
```

---

## 🔍 数据验证

### 验证数据库数据

```bash
# 检查数据库连接
psql -h localhost -U postgres -d sport_agent -c "SELECT COUNT(*) FROM matches;"

# 查看所有球队
psql -h localhost -U postgres -d sport_agent -c "SELECT team_id, team_name FROM teams;"

# 查看比赛记录
psql -h localhost -U postgres -d sport_agent -c "SELECT match_id, home_team_id, away_team_id, home_score, away_score, status FROM matches LIMIT 5;"
```

### 运行数据质量监控

```bash
python src/data_pipeline/data_quality_monitor.py
```

**预期报告**：
```
📊 数据质量监控报告
════════════════════════════════════════════════════════════
⏰ 检查时间: 2025-11-24T10:00:00Z
🏥 健康状态: HEALTHY
⚠️  告警数量: 0

📈 关键指标:
  - 总比赛数: 2
  - 最后更新: N/A 小时前
  - 未来7天比赛: 1 场
```

---

## 🧪 高级测试

### 测试 1: 数据摄取（需要 API Key）

```bash
# 从 football-data.org 拉取真实数据
python src/data_pipeline/ingest_football_data_v2.py
```

**注意**：这会消耗 API 配额，建议谨慎使用。

---

### 测试 2: 压力测试

```bash
# 安装 Apache Bench
brew install apache-bench  # macOS
# 或
sudo apt-get install apache2-utils  # Linux

# 执行压力测试（100个请求，10个并发）
ab -n 100 -c 10 -p query.json -T application/json \
  http://localhost:8080/api/v1/agent/query/v2
```

**query.json**：
```json
{"query": "曼联"}
```

---

### 测试 3: 性能基准测试

```python
# 创建性能测试脚本
import time
import asyncio
from src.agent.tools.match_tool import match_tool

async def benchmark():
    start = time.time()
    for i in range(100):
        await match_tool.get_recent_matches("曼联")
    end = time.time()
    print(f"100次查询耗时: {end - start:.2f}秒")
    print(f"平均每次: {(end - start) / 100 * 1000:.2f}ms")

asyncio.run(benchmark())
```

---

## 🐛 故障排查

### 问题 1: API 服务无法启动

**症状**：
```
ERROR: [Errno 48] Address already in use
```

**解决方案**：
```bash
# 查找占用端口的进程
lsof -i :8080

# 杀死进程
kill -9 <PID>

# 或使用不同端口
uvicorn src.services.api.main:app --reload --port 8081
```

---

### 问题 2: 数据库连接失败

**症状**：
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案**：
```bash
# 检查 PostgreSQL 状态
brew services list | grep postgresql  # macOS
systemctl status postgresql           # Linux

# 启动 PostgreSQL
brew services start postgresql        # macOS
sudo systemctl start postgresql       # Linux

# 验证连接
psql -h localhost -U postgres -c "SELECT version();"
```

---

### 问题 3: 数据库为空

**症状**：
```
系统提示：未找到球队"曼联"。
```

**解决方案**：
```bash
# 运行数据库迁移
alembic upgrade head

# 播种测试数据
python scripts/seed_db.py

# 或者拉取真实数据
python src/data_pipeline/ingest_football_data_v2.py
```

---

### 问题 4: LLM 调用失败

**症状**：
```
LLM generation failed: ...
```

**解决方案**：
```bash
# 检查 API Key 配置
cat config/service.yaml | grep api_key

# 或设置环境变量
export SPORT_AGENT__SERVICE__AGENT__LLM__API_KEY="your_key_here"

# 测试 LLM 连接
python test_llm.py
```

---

## 📊 测试覆盖率报告

### 当前测试覆盖

| 模块 | 测试脚本 | 覆盖率 | 状态 |
|-----|---------|--------|------|
| 数据管道 | `test_data_pipeline.py` | 80% | ✅ |
| Agent V2 | `test_agent_v2.py` | 70% | ✅ |
| StatsTool | `test_stats_tool.py` | 90% | ✅ |
| MatchTool | 集成在 Agent 测试中 | 85% | ✅ |
| 数据库模型 | 无专门测试 | 50% | ⚠️ |
| API 路由 | 通过 Agent 测试 | 60% | ⚠️ |

**总体覆盖率**: ~70%

---

## 🎯 测试检查清单

### 基础功能测试

- [ ] API 服务正常启动
- [ ] Swagger 文档可访问
- [ ] 数据库连接正常
- [ ] 健康检查端点响应 200

### Agent 功能测试

- [ ] V1 接口正常响应
- [ ] V2 接口正常响应
- [ ] MatchTool 返回真实数据
- [ ] StatsTool 返回正确统计
- [ ] LLM 生成合理回答

### 数据管道测试

- [ ] 实体对齐功能正常
- [ ] 数据质量监控运行
- [ ] 数据摄取（可选）成功

### 性能测试

- [ ] 单次查询延迟 < 1秒
- [ ] 100并发无错误
- [ ] 内存使用稳定

---

## 🔗 快速链接

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **健康检查**: http://localhost:8080/health

---

## 📞 获取帮助

如果遇到问题：
1. 查看日志输出
2. 检查数据库状态
3. 验证配置文件
4. 运行诊断脚本

**诊断命令**：
```bash
# 完整系统检查
python scripts/system_diagnostics.py  # 待创建
```

---

**文档版本**: v1.0.0  
**最后更新**: 2025-11-24

