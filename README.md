# Sport Agent V3 - AI 足球分析智能体系统

**一句话说明**: 企业级多智能体足球分析系统，支持智能预测、深度分析和自然语言交互

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)](https://langchain.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 项目简介

一个基于 **Supervisor + Expert Agents** 架构的 AI 足球分析系统：

### 核心能力

1. **多智能体协作**
   - SupervisorAgent（监督智能体）：任务规划、专家调度、结果合成
   - DataStatsAgent（数据专家）：查询、统计、分析
   - PredictionAgent（预测专家）：比赛预测、概率分析

2. **深度分析**
   - 球队状态分析（近期战绩、主客场表现）
   - 历史交锋分析（H2H、克制关系）
   - 积分榜查询
   - 赛程密度分析

3. **智能预测**
   - 基于多因素的概率预测
   - 可解释的预测结果（关键因素）
   - 数据质量评分

4. **自然语言交互**
   - 中文自然语言理解
   - 支持复杂问题的自动分解
   - 多步推理和综合回答

---

## 架构特点

### V3 多智能体架构

```
用户查询
    ↓
SupervisorAgent（监督智能体）
├── 任务规划
├── 专家调度
└── 结果合成
    ↓
┌───────────────┬───────────────┬───────────────┐
│ DataStats     │ Prediction    │ Knowledge     │
│ Agent         │ Agent         │ Agent         │
│               │               │ (待开发)       │
└───────────────┴───────────────┴───────────────┘
    ↓
Service 层（纯 Python，可复用）
├── DataService（数据访问）
├── StatsService（统计计算）
└── PredictService（预测逻辑）
    ↓
数据层（PostgreSQL + football-data.org API）
```

### 技术亮点

- **严格分层架构** - Agent / Service / Infra 清晰分离
- **LangChain 集成** - AgentExecutor、Tools、Memory
- **纯 Python Service** - 无 LangChain 依赖，可独立测试
- **零硬编码** - 所有配置参数可外部化
- **多 LLM 支持** - Ollama / DeepSeek / OpenAI
- **异步架构** - 全异步 I/O，高并发支持

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd "/Users/dylan/Desktop/sport agent mvp"
source .venv/bin/activate

# 启动服务
brew services start postgresql@15
brew services start ollama
```

### 2. 数据库初始化

```bash
# 创建数据库
createdb sport_agent

# 运行迁移
alembic upgrade head

# 导入种子数据
python scripts/seed_leagues.py
```

### 3. 导入数据

```bash
# 导入英超数据
python scripts/ingest_full_season.py --league=PL

# 验证数据
python scripts/check_database_status.py
```

### 4. 配置 LLM

```bash
# 查看可用模型
ollama list

# 设置模型（如果需要）
export LLM_MODEL="qwen2.5:7b"
```

### 5. 运行测试

```bash
# 测试 V3 架构
python -m scripts.test_agent_v3
```

**详细指南**: 查看 [QUICK_START.md](QUICK_START.md)

---

## 使用示例

### Python API

```python
import asyncio
from src.services.agent_service_v3 import ask

async def main():
    # 简单查询
    answer = await ask("曼联最近5场比赛战绩如何？")
    print(answer)
    
    # 复杂分析（自动调度多个专家）
    answer = await ask("曼联和利物浦谁更强？为什么？")
    print(answer)
    
    # 比赛预测
    answer = await ask("阿森纳对曼城谁会赢？")
    print(answer)

asyncio.run(main())
```

### 测试脚本

```bash
# V3 架构测试
python -m scripts.test_agent_v3

# 数据库检查
python scripts/check_database_status.py

# 数据导入
python scripts/ingest_full_season.py
```

---

## 项目结构

```
sport agent mvp/
├── src/
│   ├── supervisor/           # 监督智能体
│   │   ├── supervisor_agent.py      # SupervisorAgent 核心
│   │   └── expert_registry.py       # Expert 注册表
│   ├── agent/                # Expert Agents
│   │   ├── data_stats_agent.py      # 数据统计专家
│   │   ├── prediction_agent.py      # 预测专家
│   │   └── tools/                   # Agent 工具
│   ├── services/             # Service 层（纯 Python）
│   │   ├── data_service.py          # 数据访问服务
│   │   ├── stats_service.py         # 统计计算服务
│   │   ├── predict_service.py       # 预测服务
│   │   ├── config.py                # 配置管理
│   │   └── agent_service_v3.py      # V3 统一入口
│   ├── infra/                # 基础设施
│   │   └── db/
│   │       ├── models.py            # 数据库模型
│   │       └── session.py           # 会话管理
│   ├── shared/               # 共享组件
│   │   └── llm_client_v2.py         # LLM 客户端
│   └── data_pipeline/        # 数据管道
│       └── ingest_football_data_v2.py
├── scripts/                  # 工具脚本
│   ├── test_agent_v3.py             # V3 测试
│   ├── check_database_status.py     # 数据库检查
│   ├── ingest_full_season.py        # 数据导入
│   └── seed_leagues.py              # 种子数据
├── docs/                     # 文档
│   ├── SportAgent_TechSpec_v2_FULL.md  # V3 技术规范
│   ├── DATA_INGESTION_FAQ.md           # 数据导入FAQ
│   └── DATABASE_QUERY_GUIDE.md         # 数据库指南
├── alembic/                  # 数据库迁移
├── config/                   # 配置文件
├── QUICK_START.md            # 快速启动指南
├── START_HERE.md             # 新手入门
└── README.md                 # 本文档
```

---

## 技术栈

### 核心技术

| 分类 | 技术 | 用途 |
|------|------|------|
| **语言** | Python 3.10+ | 主要开发语言 |
| **框架** | FastAPI | 异步 Web 框架 |
| **AI 框架** | LangChain | Agent、Tools、Memory |
| **数据库** | PostgreSQL 15 | 主数据库 |
| **ORM** | SQLAlchemy 2.0 | 异步 ORM |
| **LLM** | Ollama / DeepSeek / OpenAI | 大语言模型 |
| **数据验证** | Pydantic v2 | 数据模型 |

### 架构原则

1. **分层架构** - Interface → Agent → Service → Infra
2. **LangChain 边界** - 仅在 Agent/Supervisor/RAG 层使用
3. **Service 纯净性** - Service 层不依赖 LangChain/LLM
4. **异步优先** - 所有 I/O 操作异步化
5. **类型安全** - 全面使用 Python typing

---

## 系统能力

### 数据覆盖

- **联赛**: 6 个（英超、德甲、西甲、意甲、法甲、欧冠）
- **球队**: 107 支
- **比赛数据**: 900+ 场
- **更新频率**: 支持增量更新

### Agent 能力

| Agent | 能力 | 状态 |
|-------|------|------|
| **SupervisorAgent** | 任务规划、专家调度、结果合成 | 已完成 |
| **DataStatsAgent** | 数据查询、统计分析、状态评估 | 已完成 |
| **PredictionAgent** | 比赛预测、概率分析、因素识别 | 已完成 |
| **KnowledgeAgent** | 足球知识问答、规则解释 | 待开发 |

### 性能指标

- **查询响应**: < 10 秒（包含 LLM）
- **预测准确率**: 基线模型测试中
- **并发支持**: 异步架构，支持高并发

---

## 配置说明

### 环境变量

创建 `.env` 文件：

```bash
# LLM 配置
LLM_PROVIDER=ollama               # ollama | deepseek | openai
LLM_MODEL=qwen2.5:7b              # 模型名称
LLM_BASE_URL=http://localhost:11434/v1

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sport_agent

# API Key（可选）
FOOTBALL_DATA_API_KEY=your_key_here
```

### 支持的 LLM 提供商

| 提供商 | 成本 | 速度 | 中文能力 | 推荐场景 |
|--------|------|------|---------|----------|
| **Ollama (qwen2.5)** | 免费 | 快 | 优秀 | 开发测试 |
| **DeepSeek** | $0.27/1M | 中等 | 非常优秀 | 生产环境 |
| **OpenAI (GPT-4)** | $30/1M | 慢 | 良好 | 高精度场景 |

---

## 文档导航

### 新手必读

1. **[QUICK_START.md](QUICK_START.md)** - 5分钟快速启动
2. **[START_HERE.md](START_HERE.md)** - 新手入门指南
3. **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - 项目状态和进展

### 技术文档

1. **[docs/SportAgent_TechSpec_v2_FULL.md](docs/SportAgent_TechSpec_v2_FULL.md)** - V3 技术规范（必读）
2. **[docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md)** - 数据导入常见问题
3. **[docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md)** - 数据库查询指南
4. **[docs/DATA_INTENT_GUIDE.md](docs/DATA_INTENT_GUIDE.md)** - 数据意图体系
5. **[docs/TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md)** - 球队别名修复

---

## 核心特性

### 1. 多智能体协作

SupervisorAgent 自动规划任务，调度专家协作：

```python
问题: "曼联和利物浦谁更强？为什么？"

SupervisorAgent:
  1. 分解任务 → [查询曼联状态, 查询利物浦状态, 对比分析]
  2. 调度专家 → DataStatsAgent 获取数据
  3. 综合分析 → 生成全面回答

结果: 利物浦排名第2，曼联第15...（详细分析）
```

### 2. 纯 Python Service 层

业务逻辑独立于 LLM，可复用、可测试：

```python
# Service 层不依赖 LangChain/LLM
from src.services.predict_service import predict_service

# 纯预测逻辑（无 LLM）
prediction = await predict_service.predict_match("阿森纳", "曼城")
# → {"home_win": 0.45, "draw": 0.20, "away_win": 0.35}
```

### 3. 零硬编码配置

所有参数可外部化，易于调优：

```python
# src/services/config.py
class PredictionConfig(BaseSettings):
    INITIAL_HOME_WIN_PROB: float = 0.40    # 可通过环境变量覆盖
    FORM_WIN_RATE_DIFF_WEIGHT: float = 0.3
    VENUE_ADVANTAGE_WEIGHT: float = 0.2
    ...
```

### 4. LangChain 标准集成

完整的 AgentExecutor + Tools + Memory：

```python
# 标准 LangChain Agent
from langchain.agents import AgentExecutor

executor = AgentExecutor(
    agent=agent,
    tools=expert_tools,
    memory=conversation_memory,
    verbose=True
)
```

---

## 项目状态

### V3.1.3 (当前版本)

- **架构完成度**: 100%
- **核心功能**: SupervisorAgent + 2 Expert Agents
- **Service 层**: DataService / StatsService / PredictService
- **配置管理**: 零硬编码
- **文档完整度**: 100%
- **测试**: 所有测试通过

### 下一步计划

**短期（1-2周）**:
- [ ] KnowledgeAgent + RAG 系统
- [ ] 更多统计特征
- [ ] Web UI 原型

**中期（1-2月）**:
- [ ] FastAPI 生产部署
- [ ] 实时比分推送
- [ ] 模型评估报告

**长期（3-6月）**:
- [ ] Kubernetes 部署
- [ ] 监控告警系统
- [ ] A/B 测试框架

详见 [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## 维护指南

### 日常维护

```bash
# 数据更新（可设置 cron）
python scripts/ingest_full_season.py

# 数据库检查
python scripts/check_database_status.py

# 同步球队别名（新联赛时）
python scripts/sync_with_api_names.py
```

### 常见问题

**Q: LLM 模型 404 错误？**  
A: 运行 `ollama list` 查看可用模型，设置 `export LLM_MODEL="你的模型"`

**Q: 数据库连接失败？**  
A: 确保 PostgreSQL 运行中：`brew services list`

**Q: 多次数据导入会重复吗？**  
A: 不会，系统使用 UPSERT 机制，多次运行安全幂等

详见 [QUICK_START.md](QUICK_START.md) 的常见问题部分

---

## 贡献指南

欢迎贡献！请遵循：

1. **架构原则** - 遵循分层架构，LangChain 仅用于 Agent 层
2. **代码风格** - PEP 8 + Google-style docstrings
3. **类型安全** - 使用 Python typing + Pydantic
4. **异步优先** - I/O 操作使用 async/await
5. **零硬编码** - 配置参数外部化

---

## License

MIT License - 详见 [LICENSE](LICENSE)

---

## 支持

遇到问题？

1. 查阅 **[QUICK_START.md](QUICK_START.md)** 常见问题
2. 查看 **[docs/SportAgent_TechSpec_v2_FULL.md](docs/SportAgent_TechSpec_v2_FULL.md)** 技术规范
3. 提交 Issue

---

## 技术亮点

| 特性 | V2（旧） | **V3（新）** | 优势 |
|------|---------|------------|------|
| **架构** | 单体 Planner-Executor | **Supervisor + Experts** | 模块化、可扩展 |
| **Agent 数量** | 1 个 | **3 个** (1 Supervisor + 2 Experts) | 专业分工 |
| **业务逻辑** | 混在 Agent 中 | **独立 Service 层** | 可测试、可复用 |
| **LangChain** | 未使用 | **标准集成** | AgentExecutor / Tools |
| **硬编码** | ~50 个 | **0 个** | 灵活配置 |
| **代码质量** | 混杂 | **严格分层** | 清晰、可维护 |

---

## 快速开始

```bash
# 1. 准备环境
source .venv/bin/activate
brew services start postgresql@15 ollama

# 2. 初始化数据
alembic upgrade head
python scripts/seed_leagues.py

# 3. 运行测试
python -m scripts.test_agent_v3
```

**详细指南**: [QUICK_START.md](QUICK_START.md)

---

**版本**: V3.1.3  
**状态**: 生产就绪  
**架构**: Supervisor + Expert Agents  
**最后更新**: 2025-11-27
