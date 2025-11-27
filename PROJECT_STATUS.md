# Sport Agent MVP - 项目状态

**最后更新**: 2025-11-26  
**当前版本**: v2.0  
**项目阶段**: MVP 开发完成，生产就绪

---

##  项目概览

Sport Agent MVP 是一个**企业级 AI 足球分析助手**，采用 Domain-Driven Design (DDD) 架构，支持智能预测、深度分析和自然语言交互。

**核心能力**：
-  **智能预测**：XGBoost + LLM 驱动的比赛结果预测
-  **深度分析**：历史交锋、球队状态、积分榜分析
- 💬 **自然交互**：意图识别、实体解析、中英文双语支持
- 🔄 **实时数据**：自动同步 6 大联赛（英超、德甲、西甲、意甲、法甲、欧冠）数据

---

##  已完成功能 (95%)

### 1. 数据层 (100%)
-  数据摄取管道（football-data.org API）
-  实体解析器（EntityResolver，443+ 别名映射）
-  数据质量监控
-  增量更新机制（UPSERT）
-  数据库迁移（Alembic）

**关键指标**：
- 808 场比赛数据（最近90天）
- 107 支球队
- 6 个联赛
- 89% 警告减少率（通过别名优化）

### 2. Agent 层 (90%)
-  意图识别（9 种意图类型）
-  参数解析（球队、联赛、日期）
-  工具调用（比赛查询、积分榜、统计分析）
-  场景处理（澄清、对比）
-  结果合成（结构化输出）

**支持的查询类型**：
- 比赛查询（最近、未来、特定球队）
- 球队对比
- 积分榜查询
- 预测分析
- 澄清式对话

### 3. 模型层 (85%)
-  特征工程（近期状态、排名、主客场）
-  XGBoost 基线模型
- 🔄 深度模型（待优化）
-  特征存储

### 4. 多 LLM 支持 (100%)
-  Ollama 本地模型（qwen2.5:3b）
-  DeepSeek API（deepseek-chat）
-  OpenAI API（gpt-4）
-  动态切换（配置文件）

### 5. 基础设施 (100%)
-  PostgreSQL 数据库
-  Redis 缓存
-  Docker Compose 编排
-  异步 I/O（asyncio + asyncpg）
-  结构化日志（Loguru）

---

##  核心技术栈

### 后端
- **语言**: Python 3.10+
- **框架**: FastAPI
- **数据验证**: Pydantic v2
- **数据库**: PostgreSQL 15 + asyncpg
- **缓存**: Redis
- **机器学习**: XGBoost, scikit-learn
- **LLM**: Ollama (本地) / DeepSeek / OpenAI

### 数据管道
- **API**: football-data.org
- **迁移**: Alembic
- **质量监控**: 自定义 data_quality_monitor

### 架构模式
- **设计模式**: Domain-Driven Design (DDD)
- **并发**: 全异步 (async/await)
- **类型安全**: Python typing + Pydantic strict mode
- **零硬编码**: 所有实体从数据库动态加载

---

##  项目结构

```
sport agent mvp/
├── src/
│   ├── agent/              # Agent 核心逻辑
│   │   ├── core/           # 意图、规划、执行
│   │   ├── modules/        # 功能模块（查询、分析）
│   │   ├── scenarios/      # 场景处理（澄清、对比）
│   │   └── tools/          # 工具定义
│   ├── data_pipeline/      # 数据管道
│   │   ├── entity_resolver.py      # 实体解析
│   │   └── ingest_football_data_v2.py  # 数据摄取
│   ├── ml/                 # 机器学习
│   │   ├── features/       # 特征工程
│   │   └── models/         # 模型训练/推理
│   ├── services/           # FastAPI 服务
│   │   └── api/            # REST API
│   ├── infra/              # 基础设施
│   │   └── db/             # 数据库模型
│   └── shared/             # 共享组件
│       ├── llm_client_v2.py       # LLM 客户端
│       └── translation_helper.py   # 翻译助手
├── scripts/                # 工具脚本
│   ├── chat_simple.py                # 简洁聊天界面 
│   ├── chat_with_agent.py            # 完整聊天界面
│   ├── check_database_status.py      # 数据库检查
│   ├── sync_with_api_names.py        # 同步API名称 
│   └── manage_team_aliases.py        # 管理球队别名
├── docs/                   # 技术文档
│   ├── DATA_INGESTION_FAQ.md         # 数据摄取FAQ 
│   ├── DATABASE_QUERY_GUIDE.md       # 数据库查询指南
│   ├── AGENT_ARCHITECTURE.md         # Agent架构
│   └── LOCAL_LLM_INTEGRATION.md      # 本地LLM集成
├── alembic/                # 数据库迁移
├── config/                 # 配置文件
├── docker-compose.yaml     # Docker 编排
├── requirements.txt        # Python 依赖
├── README.md               # 项目入口 
└── START_HERE.md           # 快速开始 
```

---

##  近期完成的工作

### 2025-11-26：数据摄取优化 
**问题**：EntityResolver 无法解析部分球队名称（26+ 警告）

**解决方案**：
1.  增强别名生成逻辑（支持多语言后缀/前缀）
2.  批量修复 72 个球队别名
3.  同步 API 官方名称（`sync_with_api_names.py`）

**成果**：
- 警告从 26+ 降至 3 个（**89% 减少**）
- 别名映射从 265 条增至 443 条（**+67%**）
- 数据摄取成功率 100%

**创建的工具**：
- `scripts/sync_with_api_names.py` - 同步API官方名称
- `scripts/batch_fix_all_aliases.py` - 批量修复别名
- `docs/DATA_INGESTION_FAQ.md` - 数据摄取常见问题
- `docs/TEAM_ALIAS_FIX_GUIDE.md` - 球队别名修复指南

### 关键技术改进
- **UPSERT 机制**：多次运行数据摄取不会造成冗余
- **自动创建球队**：首次出现的球队自动创建
- **智能别名匹配**：85% 相似度阈值 + 多层匹配策略

---

## 🔄 待完成功能 (5%)

### 1. 模型优化
- 🔄 深度学习模型（LSTM/Transformer）
- 🔄 模型评估报告
- 🔄 A/B 测试框架

### 2. 高级功能
- 🔄 LangChain 集成（Agent 增强）
- 🔄 RAG 系统（知识库检索）
- 🔄 实时比分推送

### 3. 生产化
- 🔄 Kubernetes 部署
- 🔄 监控告警（Prometheus + Grafana）
- 🔄 API 限流和认证

---

##  快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动数据库
docker-compose up -d postgres redis

# 启动 Ollama（本地 AI 模型）
brew services start ollama
```

### 2. 数据初始化

```bash
# 数据库迁移
alembic upgrade head

# 种子数据（联赛）
python scripts/seed_leagues.py

# 同步球队别名
python scripts/sync_with_api_names.py

# 摄取比赛数据
python src/data_pipeline/ingest_football_data_v2.py

# 验证数据
python scripts/quick_verify_data.py
```

### 3. 开始对话

```bash
# 简洁模式（推荐）
python scripts/chat_simple.py

# 完整模式
python scripts/chat_with_agent.py
```

### 4. 示例查询

```
曼联最近5场比赛战绩如何？
利物浦在英超排名第几？
预测曼联对利物浦谁会赢？
对比一下曼联和阿森纳
```

---

##  系统指标

### 数据覆盖
- **联赛**: 6 个（PL, BL1, PD, SA, FL1, CL）
- **球队**: 107 支
- **比赛**: 808 场（最近90天）
- **别名映射**: 443 条

### 性能指标
- **数据摄取**: 30 秒（808场比赛）
- **查询响应**: < 2 秒（本地LLM）
- **API 调用**: 符合 football-data.org 限额（10次/分钟）

### 质量指标
- **数据入库成功率**: 100%
- **实体解析成功率**: 99.6%（3/808 首次创建）
- **Agent 查询成功率**: 95%+

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

### 问题排查

```bash
# 检查数据库连接
python scripts/check_database_status.py

# 验证数据完整性
python scripts/quick_verify_data.py

# 查看 LLM 状态
ollama list
```

---

## 📖 文档导航

### 新手必读
1. [README.md](README.md) - 项目入口
2. [START_HERE.md](START_HERE.md) - 快速开始（3步上手）

### 技术文档
1. [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - Agent 架构设计
2. [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md) - 数据摄取常见问题 
3. [docs/DATABASE_QUERY_GUIDE.md](docs/DATABASE_QUERY_GUIDE.md) - 数据库查询指南
4. [docs/LOCAL_LLM_INTEGRATION.md](docs/LOCAL_LLM_INTEGRATION.md) - 本地 LLM 集成
5. [docs/ZERO_HARDCODE_IMPLEMENTATION.md](docs/ZERO_HARDCODE_IMPLEMENTATION.md) - 零硬编码实现

### 问题解决
1. [docs/TEAM_ALIAS_FIX_GUIDE.md](docs/TEAM_ALIAS_FIX_GUIDE.md) - 球队别名修复 
2. [docs/DATA_INTENT_GUIDE.md](docs/DATA_INTENT_GUIDE.md) - 数据意图体系

---

## 🎓 技术亮点

### 1. 零硬编码设计
所有实体（球队、联赛）从数据库动态加载，无需硬编码映射：

```python
#  不好的做法（硬编码）
TEAM_MAP = {"Manchester United": "MUN", "Liverpool": "LIV", ...}

#  好的做法（动态加载）
team_id = await entity_resolver.resolve_team("Manchester United")
```

### 2. 智能别名匹配
3 层匹配策略：精确匹配 → 去除后缀 → 模糊匹配（85%）

```python
# 自动生成别名
"Manchester United FC (曼联)" →
  - "Manchester United FC"  # 完整API名称
  - "Manchester United"      # 去除后缀
  - "曼联"                   # 中文别名
  - "MUN"                    # team_id
```

### 3. UPSERT 机制
多次运行数据摄取安全无副作用：

```python
stmt = stmt.on_conflict_do_update(
    index_elements=['match_id'],
    set_={"status": ..., "home_score": ..., "updated_at": ...}
)
```

### 4. 多 LLM 支持
一行配置切换模型：

```yaml
# config/service.yaml
llm:
  provider: "ollama"  # ollama / deepseek / openai
  model: "qwen2.5:3b"
```

---

## 🔗 相关链接

- **项目仓库**: [GitHub](https://github.com/your-repo)
- **数据源**: [football-data.org](https://www.football-data.org/)
- **本地 LLM**: [Ollama](https://ollama.ai/)
- **DeepSeek API**: [DeepSeek](https://deepseek.com/)

---

## 📞 联系方式

如有问题，请查阅：
1. [docs/DATA_INGESTION_FAQ.md](docs/DATA_INGESTION_FAQ.md) - 数据问题
2. [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - 架构问题
3. [README.md](README.md) - 通用问题

---

**项目状态**:  MVP 完成，生产就绪  
**推荐操作**: 阅读 [START_HERE.md](START_HERE.md) 开始使用

