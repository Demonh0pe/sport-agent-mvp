# Sport Agent V3 快速启动

**版本**: V3.1.3  
**状态**:  生产就绪

---

##  5 分钟快速启动

### 1. 环境准备

```bash
# 激活虚拟环境
cd "/Users/dylan/Desktop/sport agent mvp"
source .venv/bin/activate

# 启动 PostgreSQL
brew services start postgresql@15

# 启动 Ollama（本地LLM）
brew services start ollama
```

### 2. 数据库初始化

```bash
# 创建数据库（首次）
createdb sport_agent

# 运行迁移
alembic upgrade head

# 导入种子数据
python scripts/seed_leagues.py
```

### 3. 导入比赛数据

```bash
# 导入英超数据
python scripts/ingest_full_season.py --league=PL

# 验证数据（可选）
python scripts/check_database_status.py
```

### 4. 配置 LLM 模型

```bash
# 查看已有模型
ollama list

# 如果需要，拉取推荐模型
ollama pull qwen2.5:7b

# 设置环境变量
export LLM_MODEL="qwen2.5:7b"
```

### 5. 运行测试

```bash
# 测试 V3 架构
python -m scripts.test_agent_v3
```

---

##  示例对话

### 数据查询
```
问：曼联最近5场比赛战绩如何？
答：曼联最近5场：2胜1平2负，进7球失6球
```

### 比赛预测
```
问：阿森纳对曼城谁会赢？
答：预测曼城获胜（概率 45%），关键因素...
```

### 综合分析
```
问：曼联和利物浦谁更强？为什么？
答：利物浦目前排名第2，战绩更优...（自动调度多个专家分析）
```

---

##  环境检查清单

###  必需服务

- [ ] **PostgreSQL 运行中**
  ```bash
  brew services list | grep postgresql
  ```

- [ ] **Ollama 运行中**（如使用本地LLM）
  ```bash
  ollama list
  ```

- [ ] **虚拟环境激活**
  ```bash
  which python  # 应显示 .venv 路径
  ```

###  数据检查

- [ ] **数据库有数据**
  ```bash
  python scripts/check_database_status.py
  ```

- [ ] **LLM 模型可用**
  ```bash
  ollama run qwen2.5:7b "你好"
  ```

---

##  V3 架构说明

### 核心组件

```
SupervisorAgent（监督智能体）
├── DataStatsAgent（数据统计专家）
│   ├── 查询球队信息
│   ├── 查询比赛记录
│   ├── 计算统计数据
│   └── 分析球队状态
├── PredictionAgent（预测专家）
│   ├── 比赛预测
│   ├── 概率分析
│   └── 关键因素识别
└── KnowledgeAgent（知识专家）- 待开发
    └── 足球规则/历史问答
```

### 数据流

```
用户查询
  ↓
SupervisorAgent（任务规划）
  ↓
Expert Agents（专业分工）
  ↓
Service 层（业务逻辑）
  ↓
数据库/API（数据源）
```

---

##  核心脚本说明

| 脚本 | 用途 | 示例 |
|------|------|------|
| `test_agent_v3.py` | V3 架构测试 | `python -m scripts.test_agent_v3` |
| `check_database_status.py` | 数据库检查 | `python scripts/check_database_status.py` |
| `ingest_full_season.py` | 数据导入 | `python scripts/ingest_full_season.py` |
| `seed_leagues.py` | 种子数据 | `python scripts/seed_leagues.py` |
| `sync_with_api_names.py` | 同步球队别名 | `python scripts/sync_with_api_names.py` |
| `manage_team_aliases.py` | 管理别名 | `python scripts/manage_team_aliases.py` |

---

##  常见问题

### 问题1: Model 404 错误

**错误**: `model 'qwen:7b' not found`

**解决**:
```bash
# 查看已有模型
ollama list

# 使用已有模型
export LLM_MODEL="你的模型名"

# 或拉取新模型
ollama pull qwen2.5:7b
export LLM_MODEL="qwen2.5:7b"
```

### 问题2: 数据库连接失败

**错误**: `could not connect to server`

**解决**:
```bash
# 检查状态
brew services list

# 启动 PostgreSQL
brew services start postgresql@15

# 测试连接
psql -d sport_agent -c "SELECT 1"
```

### 问题3: 数据为空

**错误**: 查询返回空结果

**解决**:
```bash
# 检查数据
python scripts/check_database_status.py

# 导入数据
python scripts/seed_leagues.py
python scripts/ingest_full_season.py
```

### 问题4: 依赖缺失

**错误**: `ModuleNotFoundError`

**解决**:
```bash
# 安装 LangChain 依赖
pip install langchain-openai langchain-core langchain-community langchain

# 安装数据库依赖
pip install sqlalchemy[asyncio] asyncpg

# 或安装所有依赖
pip install -r requirements.txt
```

---

##  文档导航

### 核心文档
- **README.md** - 项目概览
- **START_HERE.md** - 新手入门
- **PROJECT_STATUS.md** - 项目状态

### 技术文档
- **docs/SportAgent_TechSpec_v2_FULL.md** - V3 技术规范 
- **docs/DATA_INGESTION_FAQ.md** - 数据导入常见问题
- **docs/DATABASE_QUERY_GUIDE.md** - 数据库查询指南
- **docs/DATA_INTENT_GUIDE.md** - 数据意图体系
- **docs/TEAM_ALIAS_FIX_GUIDE.md** - 球队别名修复

---

##  Python API 使用

### 方式1: 简洁接口（推荐）

```python
import asyncio
from src.services.agent_service_v3 import ask

async def main():
    # 自动调度 Supervisor + Experts
    answer = await ask("曼联最近状态如何？")
    print(answer)

asyncio.run(main())
```

### 方式2: 直接调用 Expert

```python
import asyncio
from src.services.agent_service_v3 import ask_expert

async def main():
    # 只调用 DataStats Expert
    answer = await ask_expert("data_stats", "曼联最近5场战绩")
    print(answer)
    
    # 只调用 Prediction Expert
    answer = await ask_expert("prediction", "阿森纳对曼城")
    print(answer)

asyncio.run(main())
```

### 方式3: Service 层（无 LLM）

```python
import asyncio
from src.services.data_service import data_service
from src.services.predict_service import predict_service

async def main():
    # 纯数据查询（不使用 LLM）
    team = await data_service.get_team("曼联")
    matches = await data_service.get_recent_matches("曼联", last_n=5)
    
    # 纯预测计算（不使用 LLM）
    prediction = await predict_service.predict_match("阿森纳", "曼城")
    print(f"胜率: {prediction['probabilities']}")

asyncio.run(main())
```

---

##  配置说明

### 环境变量

创建 `.env` 文件：

```bash
# LLM 配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
LLM_BASE_URL=http://localhost:11434/v1

# 数据库配置
DATABASE_URL=postgresql+asyncpg://sport_agent_user:password@localhost:5432/sport_agent

# API Key（可选）
FOOTBALL_DATA_API_KEY=your_api_key_here
```

### 支持的 LLM 提供商

| 提供商 | LLM_PROVIDER | LLM_MODEL | 说明 |
|--------|--------------|-----------|------|
| **Ollama** | `ollama` | `qwen2.5:7b` | 本地运行，免费 |
| **DeepSeek** | `deepseek` | `deepseek-chat` | 便宜，中文好 |
| **OpenAI** | `openai` | `gpt-4` | 强大，较贵 |

---

##  验证成功

成功运行后，你会看到：

```
============================================================
测试 Agent Service V3 新架构
============================================================

1. 可用的专家：
   ['data_stats', 'prediction']

2. 测试数据查询专家（DataStatsAgent）
   问题：曼联最近5场比赛战绩如何？

> Entering new AgentExecutor chain...
曼联 近 5 场战绩：
- 胜/平/负: 3胜 1平 1负
- 胜率: 60.0%
 成功！

3. 测试预测专家（PredictionAgent）
   【阿森纳 vs 曼城 预测分析】
   预测结果: 曼城获胜
 成功！

============================================================
测试完成
============================================================
```

---

##  下一步

### 1. 开始使用
```bash
python -m scripts.test_agent_v3
```

### 2. 集成到应用
```python
from src.services.agent_service_v3 import ask
answer = await ask("你的问题")
```

### 3. 部署到生产
- 参考 `docs/SportAgent_TechSpec_v2_FULL.md`

---

**准备好了？** 运行 `python -m scripts.test_agent_v3` 开始测试！
