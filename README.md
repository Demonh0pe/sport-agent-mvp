# Sport Agent MVP - AI 足球分析助手

**一句话说明**: 企业级 AI 足球分析助手，支持智能预测、深度分析和自然语言交互

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🎯 这个项目是什么？

一个 **AI 驱动的足球分析助手**，可以：

1. **🤖 智能预测** - 基于 XGBoost + LLM 预测比赛结果，给出概率和理由
2. **📊 深度分析** - 分析球队状态、历史交锋、战术克制、积分榜
3. **💬 自然交互** - 中英文双语，支持模糊查询、澄清对话、对比分析
4. **🔄 实时数据** - 自动同步 6 大联赛数据（英超、德甲、西甲、意甲、法甲、欧冠）

### 示例对话

```
你: 曼联最近5场比赛战绩如何？

AI: 曼联最近5场比赛：
  ✅ 11/23 曼联 3-0 莱斯特城（主场胜）
  ❌ 11/10 曼联 1-3 布莱顿（客场负）
  ✅ 11/03 曼联 2-0 切尔西（主场胜）
  ⚖️  10/27 曼联 1-1 西汉姆（客场平）
  ❌ 10/19 曼联 0-2 利物浦（主场负）

战绩总结：2胜1平2负，进7球失6球
```

```
你: 预测曼联对阿森纳谁会赢？

AI: 预测结果：阿森纳客场获胜 (73.2%)

数据支撑：
  1. 排名差距：阿森纳第2 (31分)，曼联第15 (18分)
  2. 近期状态：阿森纳近5场3胜，曼联2胜
  3. 历史交锋：最近一次阿森纳2-0获胜

关键因素：
  ✅ 阿森纳状态更好，整体实力占优
  ⚠️  曼联有主场优势，可能爆冷
```

---

## 🚀 快速开始（3步）

### 1. 环境准备

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动数据库（PostgreSQL + Redis）
docker-compose up -d postgres redis

# 启动本地 AI 模型（Ollama）
brew services start ollama
# 或者
ollama serve
```

### 2. 数据初始化（首次使用）

```bash
# 数据库迁移
alembic upgrade head

# 种子数据（联赛信息）
python scripts/seed_leagues.py

# 同步球队别名
python scripts/sync_with_api_names.py

# 摄取比赛数据（最近90天）
python src/data_pipeline/ingest_football_data_v2.py

# 验证数据（可选）
python scripts/quick_verify_data.py
```

### 3. 开始对话

```bash
# 简洁模式（推荐）⭐
python scripts/chat_simple.py

# 完整模式（显示推理过程）
python scripts/chat_with_agent.py
```

### 4. 试试这些问题

```
曼联最近5场比赛战绩如何？
利物浦在英超排名第几？
预测曼联对利物浦谁会赢？
对比一下曼联和阿森纳
拜仁慕尼黑的主场战绩怎么样？
```

---

## 📁 项目结构

```
sport agent mvp/
├── src/
│   ├── agent/              # Agent 核心（意图识别、工具调用、推理）
│   ├── data_pipeline/      # 数据管道（摄取、清洗、实体解析）
│   ├── ml/                 # 机器学习（特征工程、模型训练）
│   ├── services/           # FastAPI 服务
│   ├── infra/              # 基础设施（数据库模型）
│   └── shared/             # 共享组件（LLM客户端、翻译）
├── scripts/                # 工具脚本
│   ├── chat_simple.py                # 简洁聊天 ⭐
│   ├── check_database_status.py      # 数据库检查 ⭐
│   └── sync_with_api_names.py        # 同步API名称 ⭐
├── docs/                   # 技术文档
│   ├── DATA_INGESTION_FAQ.md         # 数据摄取FAQ ⭐
│   ├── AGENT_ARCHITECTURE.md         # Agent架构
│   └── DATABASE_QUERY_GUIDE.md       # 数据库查询
├── alembic/                # 数据库迁移
├── config/                 # 配置文件
├── docker-compose.yaml     # Docker 编排
└── requirements.txt        # Python 依赖
```

---

## 🛠️ 技术栈

### 核心技术
- **语言**: Python 3.10+
- **框架**: FastAPI（异步）
- **数据验证**: Pydantic v2（严格模式）
- **数据库**: PostgreSQL 15 + asyncpg
- **缓存**: Redis
- **机器学习**: XGBoost, scikit-learn
- **LLM**: Ollama (本地) / DeepSeek / OpenAI

### 架构特点
- ✅ **Domain-Driven Design (DDD)** - 清晰的领域模型
- ✅ **异步优先** - 全异步 I/O，高并发支持
- ✅ **类型安全** - Python typing + Pydantic strict mode
- ✅ **零硬编码** - 所有实体从数据库动态加载
- ✅ **多 LLM 支持** - 一行配置切换模型

---

## 📊 系统能力

### 数据覆盖
- **联赛**: 6 个（英超、德甲、西甲、意甲、法甲、欧冠）
- **球队**: 107 支
- **比赛数据**: 808 场（最近90天）
- **自动更新**: 支持增量更新（UPSERT 机制）

### Agent 能力
支持 9 种查询意图：
1. **比赛查询** - 查询历史/未来比赛
2. **球队对比** - 对比两支球队的状态、排名
3. **积分榜** - 查询联赛积分榜
4. **预测分析** - 预测比赛结果（含概率）
5. **澄清对话** - 处理模糊查询
6. **统计查询** - 球队统计数据
7. **新闻查询** - 足球新闻（待开发）
8. **知识问答** - 足球规则、历史（待开发）
9. **闲聊** - 通用对话

### 性能指标
- **数据摄取**: 30 秒（808场比赛）
- **查询响应**: < 2 秒（本地LLM）
- **实体解析成功率**: 99.6%
- **Agent 查询成功率**: 95%+

---

## 🔧 配置说明

### 切换 LLM 模型

编辑 `config/service.yaml`:

```yaml
llm:
  # 本地模型（免费，速度快）
  provider: "ollama"
  model: "qwen2.5:3b"
  
  # DeepSeek（便宜，效果好）
  # provider: "deepseek"
  # model: "deepseek-chat"
  # api_key: "your-api-key"
  
  # OpenAI（强大，较贵）
  # provider: "openai"
  # model: "gpt-4"
  # api_key: "your-api-key"
```

### 数据源配置

编辑 `.env` 或环境变量：

```bash
# Football-data.org API Key（必需）
FOOTBALL_DATA_API_KEY=your_api_key_here

# 数据库连接
DATABASE_URL=postgresql+asyncpg://sport_agent:password@localhost:5432/sport_agent_db

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## 📖 文档导航

### 🆕 新手必读
1. **[START_HERE.md](START_HERE.md)** - 3步快速上手 ⭐
2. **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - 当前项目状态和进展 ⭐
3. 本文档（README.md）- 项目概览

### 📚 技术文档
1. **[docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md)** - 数据摄取常见问题（重复运行是否冗余？如何解决无法解析？）⭐
2. **[docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md)** - Agent 架构设计（意图识别、工具调用、推理引擎）
3. **[docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md)** - 数据库查询指南（SQL 示例）
4. **[docs/LOCAL_LLM_INTEGRATION.md](docs/LOCAL_LLM_INTEGRATION.md)** - 本地 LLM 集成（Ollama 配置）
5. **[docs/ZERO_HARDCODE_IMPLEMENTATION.md](docs/ZERO_HARDCODE_IMPLEMENTATION.md)** - 零硬编码实现原理

### 🔧 问题解决
1. **[docs/TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md)** - 球队别名修复（解决"无法解析球队名称"警告）⭐
2. **[docs/DATA_INTENT_GUIDE.md](docs/DATA_INTENT_GUIDE.md)** - 数据意图体系（理解 Agent 如何识别用户意图）

---

## 🛠️ 维护指南

### 日常维护

```bash
# 每日数据更新（可设置 cron job）
python src/data_pipeline/ingest_football_data_v2.py

# 每周检查数据库状态
python scripts/check_database_status.py

# 每月同步球队别名（有新联赛/球队时）
python scripts/sync_with_api_names.py
```

### 常见问题

**Q: 多次运行数据摄取会造成数据冗余吗？**  
A: 不会。系统使用 UPSERT 机制，多次运行只会更新最新数据。详见 [DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md#q1-多次运行数据摄取会造成数据冗余吗)

**Q: 出现"无法解析球队名称"警告怎么办？**  
A: 运行 `python scripts/sync_with_api_names.py` 同步球队别名。详见 [TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md)

**Q: 如何切换 LLM 模型？**  
A: 编辑 `config/service.yaml` 中的 `llm.provider` 和 `llm.model`。支持 ollama / deepseek / openai。

**Q: 数据库连接失败？**  
A: 确保 Docker 容器运行：`docker-compose ps`。检查 `.env` 中的 `DATABASE_URL`。

---

## 🎯 核心特性

### 1. 零硬编码设计 ⭐

所有实体（球队、联赛）从数据库动态加载，无需硬编码映射：

```python
# ❌ 不好的做法（硬编码）
TEAM_MAP = {"Manchester United": "MUN", "Liverpool": "LIV", ...}

# ✅ 好的做法（动态加载）
team_id = await entity_resolver.resolve_team("Manchester United")
```

**优势**：
- 添加新球队/联赛无需修改代码
- 支持多语言别名（中英文）
- 自动处理 API 名称变化

### 2. 智能别名匹配 ⭐

3 层匹配策略：精确匹配 → 去除后缀 → 模糊匹配（85%）

```python
# 自动生成别名
"Manchester United FC (曼联)" →
  - "Manchester United FC"  # 完整API名称
  - "Manchester United"      # 去除后缀
  - "曼联"                   # 中文别名
  - "MUN"                    # team_id
```

**成果**：
- 443+ 别名映射
- 99.6% 解析成功率
- 支持模糊查询（"曼联" / "曼" / "MUN"）

### 3. 多 LLM 支持 ⭐

一行配置切换模型，无需修改代码：

| 模型 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **Ollama (qwen2.5:3b)** | 免费、快速、本地运行 | 推理能力一般 | 开发测试、演示 |
| **DeepSeek** | 便宜（$0.27/1M tokens）、中文好 | 需要网络 | 生产环境（推荐）|
| **OpenAI (GPT-4)** | 推理能力强 | 贵（$30/1M tokens）| 高精度场景 |

### 4. UPSERT 机制 ⭐

多次运行数据摄取安全无副作用：

```python
stmt = stmt.on_conflict_do_update(
    index_elements=['match_id'],  # 基于 match_id 唯一键
    set_={"status": ..., "home_score": ..., "updated_at": ...}
)
```

**优势**：
- 安全幂等（多次运行结果一致）
- 支持增量更新（只更新变化的数据）
- 自动更新比分、状态

---

## 📊 项目状态

- ✅ **MVP 完成** (95%)
- ✅ **数据层** (100%) - 摄取、解析、质量监控
- ✅ **Agent 层** (90%) - 意图识别、工具调用、场景处理
- ✅ **模型层** (85%) - 特征工程、XGBoost 基线
- ✅ **多 LLM** (100%) - Ollama / DeepSeek / OpenAI
- ✅ **基础设施** (100%) - PostgreSQL / Redis / Docker

详见 [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## 🚀 下一步计划

### 短期（1-2周）
- [ ] LangChain 集成（增强 Agent 能力）
- [ ] RAG 系统（知识库检索）
- [ ] 模型评估报告（Precision / Recall / F1）

### 中期（1-2月）
- [ ] Web UI（React + FastAPI）
- [ ] 实时比分推送（WebSocket）
- [ ] A/B 测试框架

### 长期（3-6月）
- [ ] Kubernetes 部署
- [ ] 监控告警（Prometheus + Grafana）
- [ ] 多租户支持

---

## 🤝 贡献指南

欢迎贡献！请遵循以下原则：

1. **代码风格**: 遵循 PEP 8，使用 Google-style docstrings
2. **类型安全**: 使用 Python typing 和 Pydantic v2
3. **异步优先**: I/O 操作使用 async/await
4. **零硬编码**: 实体从数据库加载，不硬编码映射
5. **测试**: 使用 pytest，覆盖率 > 80%

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 📞 联系方式

如有问题：
1. 查阅 [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md)
2. 查看 [PROJECT_STATUS.md](PROJECT_STATUS.md)
3. 提交 Issue 或 PR

---

## 🎓 技术亮点总结

| 特性 | 传统做法 | 本项目做法 | 优势 |
|------|---------|-----------|------|
| **实体映射** | 硬编码字典 | 数据库动态加载 | 易扩展、多语言 |
| **别名匹配** | 精确匹配 | 3层匹配（精确+去缀+模糊）| 99.6% 成功率 |
| **数据更新** | INSERT（重复报错）| UPSERT（幂等）| 安全、增量 |
| **LLM 切换** | 修改代码 | 配置文件 | 1行切换 |
| **并发处理** | 同步阻塞 | 异步非阻塞 | 高并发 |

---

**开始使用**: 阅读 [START_HERE.md](START_HERE.md) 快速上手 🚀
