````markdown
# Sport Agent 技术实现文档（v0.1，第 1–3 章）

> 本文档面向工程实现与团队协作，重点说明：系统边界、架构设计、技术栈与依赖。  
> 所有内容以“能落地编码”为目标，不展开产品层面的愿景描述。

---

## 1. 项目概述（Overview）

### 1.1 系统边界（Scope）

**当前阶段（V1）系统能力：**

- 赛事范围：足球（Football）
  - 数据源：`football-data.org` REST API
- 功能范围：
  1. **结构化数据查询**
     - 联赛列表：可用的 competitions（例如 EPL, La Liga 等）
     - 指定日期 / 轮次 / 联赛的比赛列表
     - 单场比赛详情（队伍、时间、比分、状态）
     - 联赛积分榜
  2. **球队状态与特征分析**
     - 近 N 场胜/平/负
     - 近 N 场进球 / 失球 / 净胜球
     - 主客场分开统计
     - 双方历史交锋（Head-to-head）
  3. **胜平负预测（Baseline）**
     - 基于结构化特征（近况、主客场、H2H 等）
     - 使用简单 Elo / 规则模型（后续扩展 ML 模型）
     - 输出：`home_win / draw / away_win` 概率
  4. **解释型回答（Explainable Output）**
     - 将 Data/Stats/Prediction 的结构化结果，用 LLM 生成自然语言分析
  5. **知识问答（RAG）**
     - 足球规则（越位、犯规等）
     - 基本战术体系说明（例如 4-3-3、反击、高位逼抢）
     - 历史与背景知识（非实时）
  6. **对话交互**
     - 单轮/多轮自然语言对话
     - 会话内上下文记忆和追问（例如“那曼城最近状态呢？”）

**明确不在当前版本范围内：**

- 实时赔率盘口、博彩对接
- 用户账号体系 / 登录 / 个人主页
- 复杂推荐系统（只预留架构，不做完整实现）
- 多体育项目（NBA 等）——作为 V2 扩展

---

### 1.2 用户与使用场景（简要技术视角）

**目标调用方：**

- 内部 Web 前端 / 管理后台
- 内部工程脚本（调 REST API）
- 内部测试工具（CLI / Postman）

**典型调用方式：**

1. REST 接口：`POST /api/chat`
   - 入参：自然语言 + 可选上下文标识
   - 出参：自然语言回答 + 结构化 debug 信息（可选）
2. 数据查询接口：`GET /api/match`, `GET /api/standing` 等
   - 入参：联赛/日期/球队 ID 等
   - 出参：JSON 结构化数据

---

### 1.3 约束条件（Constraints）

- **数据约束**
  - 仅使用 `football-data.org` 提供的数据（API 有调用频率限制）
  - 本地数据库为缓存与长期存储来源，非实时数据源
- **模型约束**
  - 优先使用本地可部署开源 LLM（例如 Qwen / Llama3）
  - 对外 LLM API（如 OpenAI）作为可选 provider，不强依赖
- **资源约束**
  - 单机 / 单容器起步，后续再做水平扩展
  - GPU 可选（对本地 LLM 推理加速）

---

## 2. 整体架构设计（System Architecture）

### 2.1 高层架构（Logical View）

从“调用链”的角度描述系统结构：

```text
[Client Web/CLI/Other Services]
              │ HTTP/JSON
              ▼
        ┌────────────────┐
        │   API 层（FastAPI） │
        └───────┬────────┘
                │
                ▼
     ┌───────────────────────┐
     │  Supervisor Agent     │  ← 基于 LangChain 的监督智能体
     │  - 任务拆解           │
     │  - 专家调度           │
     │  - 结果质检/降级      │
     └────────┬────────────┘
              │
   ┌──────────┼───────────────┐
   ▼          ▼               ▼
DataStatsAgent   PredictionAgent   KnowledgeAgent
(数据/特征专家)   (预测专家)         (RAG/知识专家)
   │          │               │
   ▼          ▼               ▼
LangChain Tools (Data/Stats/Predict/Knowledge)
   │          │               │
   ▼          ▼               ▼
Service Layer（DataService / StatsService / PredictService / KnowledgeService）
   │
   ▼
Infra & Data Layer（PostgreSQL + pgvector/Chroma + Redis + football-data.org）
````

**关键点：**

* LangChain 用于：

  * Supervisor Agent：规划与调度
  * Expert Agents：不同领域的子智能体
  * Tools：将 Service 暴露为可调用的“函数工具”
  * RAG：Retriever + Chain 组合
  * Memory：对话上下文
* Service 层是业务逻辑核心，不依赖 LangChain，不直接使用 LLM。

---

### 2.2 分层与组件职责（Layered View）

#### 2.2.1 Interface Layer（API 层）

* **组件：**

  * `api/routes/chat.py`：聊天接口 `/api/chat`
  * `api/routes/data.py`：数据接口 `/api/match`, `/api/standing`, `/api/team`
* **职责：**

  * 请求验证（schema 校验）
  * 权限校验（如有）
  * 调用 `SupervisorAgent.run(query, session_id)`
  * 响应格式统一（HTTP 状态码 + JSON）

---

#### 2.2.2 Agent Layer（Supervisor + Experts）

* **组件：**

  * `src/supervisor/supervisor_agent.py`
  * `src/supervisor/expert_registry.py`
  * `src/agent/data_stats_agent.py`
  * `src/agent/prediction_agent.py`
  * `src/agent/knowledge_agent.py`
* **职责：**

  * Supervisor：

    * 接收 query + context
    * 借助 LLM（LangChain ChatModel）识别意图、规划子任务
    * 调用 Expert tools 并整合结果
    * 进行 LLM 级的结果评估（是否答对问题 / 是否缺少关键信息）
  * Experts：

    * 只关注特定领域（数据/预测/知识）
    * 内部只使用有限的一组 Tools
    * 可单独调试（便于单模块迭代）

---

#### 2.2.3 Tool Layer（LangChain Tools）

* **组件：**

  * `src/agent/tools/data_tools.py`（DataTool, StatsTool）
  * `src/agent/tools/predict_tools.py`（PredictTool）
  * `src/agent/tools/knowledge_tools.py`（KnowledgeTool）
* **职责：**

  * 定义 `@tool` 或 LangChain Tool 对象：

    * 入参：结构化（Pydantic 模型）
    * 内部：调用 Service
    * 出参：结构化字典（供 LLM 进一步使用）
  * 不包含复杂业务逻辑，不访问数据库，不直接调 HTTP。

---

#### 2.2.4 Service Layer（业务服务层）

* **组件：**

  * `src/services/data_service.py`
  * `src/services/stats_service.py`
  * `src/services/predict_service.py`
  * `src/services/knowledge_service.py`
* **职责：**

  * DataService：

    * 查询 PostgreSQL 比赛/球队/积分
    * 必要时调用 football-data.org 补数
  * StatsService：

    * 基于 DB 数据计算近况、主客场、H2H 等特征
  * PredictService：

    * 接收结构化特征
    * 调用预测模型（Elo/Poisson/ML）
    * 返回概率 + 特征贡献摘要
  * KnowledgeService：

    * 统一封装 RAG pipeline（调用 LangChain RAG，但对上层隐藏实现细节）

---

#### 2.2.5 Infra & Data Layer（基础设施与数据层）

* **组件：**

  * `src/infra/db.py`（PostgreSQL 连接 / SQLAlchemy）
  * `src/infra/redis.py`
  * `src/infra/models.py`（ORM 模型）
  * `src/data_pipeline/ingest_football_data.py`
* **职责：**

  * 提供可靠的数据持久化与缓存机制
  * 负责数据同步与质量控制（数据管道）
  * 不包含任何业务或 LLM 逻辑

---

### 2.3 典型调用流程（Example Flows）

#### 2.3.1 场景：用户问“下轮阿森纳 vs 曼城谁更有优势？”

1. 前端调用 `POST /api/chat`，body:

   ```json
   { "query": "下轮阿森纳 vs 曼城谁更有优势？", "session_id": "abc123" }
   ```
2. API 层调用 `SupervisorAgent.run(query, session_id)`
3. Supervisor 使用 LLM：

   * 解析意图：预测 + 分析
   * 生成子任务列表：

     1. 调用 DataStatsExpert 查询双方近况与特征
     2. 调用 PredictionExpert 生成胜平负概率
     3. 调用 KnowledgeExpert 生成综合性解释
4. 对每个子任务：

   * Supervisor 调用对应 Expert 的 Tool（例如 `prediction_expert_tool`）
   * Expert 内部调用 Tools → Services → DB / 模型
5. Supervisor 收集结果，做一次 LLM 级别的检查与合成，生成最终回答文本
6. API 层返回：

   ```json
   {
     "answer": "...自然语言分析...",
     "meta": {
       "prediction": {...},
       "features": {...}
     }
   }
   ```

---

## 3. 技术栈与依赖（Tech Stack）

本章明确说明：使用哪些技术、各自负责什么、约束与替代方案。

### 3.1 编程语言与基础环境

* 语言：**Python 3.11**
* 包管理：`poetry` 或 `pip-tools`（根据团队实际选择其一）
* 运行环境：

  * Dev：macOS / Linux
  * Prod：Linux（Ubuntu 20.04+），支持 Docker 部署

---

### 3.2 框架与主要库

#### 3.2.1 Web / API

* **FastAPI**

  * 职责：提供 REST 接口（/api/chat, /api/match 等）
  * 依赖：

    * `uvicorn` 作 ASGI server
    * `pydantic` 作请求/响应模型定义

#### 3.2.2 Agent / LLM 编排（关键）

* **LangChain（>= 0.3.x）**

  * 用途：

    * 定义 `SupervisorAgent`（多工具、多专家调用流水线）
    * 定义各个 `ExpertAgent`（每个 Expert 一个独立 AgentExecutor）
    * 将 Service 封装为 `Tool`（`@tool` 或 `StructuredTool`）
    * 管理 `Memory`（会话上下文）
    * 构建 `RAG` 流程（Retriever + LLM）
  * 使用模块（示例）：

    * `langchain_core.tools`
    * `langchain.agents` / `langchain_community.agent_toolkits`
    * `langchain_core.runnables`
    * `langchain.memory`

> 说明：
> LangChain 只在 **Agent 层 + Tool 层 + RAG** 出现，Service 与 Infra 层禁止直接依赖 LangChain。

#### 3.2.3 LLM 客户端

* 自定义封装：`src/shared/llm_client.py`
* 功能：

  * 支持不同 provider（本地 / 远程）
  * 暴露统一接口：

    ```python
    class LLMClient:
        def chat(self, messages: list[dict]) -> str: ...
        def as_langchain_chat_model(self): ...
    ```
* 支持的后端：

  * 本地：Ollama（例如 `qwen2.5:7b` / `llama3:8b`）
  * 远程（可选）：OpenAI GPT-4.x / DeepSeek / 其他

---

### 3.3 模型选型（LLM & Embedding）

#### 3.3.1 对话 / 推理模型（LLM）

一期建议配置（可根据机器资源微调）：

* 默认 LLM（对话 + Agent 推理）：

  * `Qwen2.5-7B-Instruct`（本地）
  * 或 `Llama-3-8B-Instruct`（英文偏多时使用）
* 要求：

  * 支持 function-calling / tools 格式（更易用 LangChain agent）
  * 可运行在单机 24G+ GPU 或低速 CPU 模式（开发时）

LLM 的具体部署方式（示例）：

* 使用 Ollama：

  * 在 `llm_client.py` 中通过 HTTP 调用本地 Ollama server；
* 或使用自建 vLLM 服务：

  * 通过 REST / OpenAI 协议调用。

#### 3.3.2 Embedding 模型（RAG）

* 模型候选：

  * `BAAI/bge-m3`
  * 或 `Alibaba-NLP/gte-base-zh` 等多语言 embedding
* 封装：

  * 通过 `sentence-transformers` 或 LangChain `HuggingFaceEmbeddings`
* 要求：

  * 支持中文 / 英文混合内容
  * 向量维度固定（512 / 768）

---

### 3.4 数据库、向量库与缓存

#### 3.4.1 关系型数据库

* **PostgreSQL 15+**

  * 存储内容：

    * 比赛数据（matches）
    * 球队信息（teams）
    * 联赛信息（competitions）
    * 积分表（standings）
    * 预计算统计（可选）
    * Agent 日志（可选）
  * ORM：

    * 推荐 `SQLAlchemy 2.x` + `Alembic` 做迁移

#### 3.4.2 向量库（RAG）

两种方案预留，选其一作为实现：

1. **pgvector（嵌入 PostgreSQL）**

   * 优点：统一 DB、部署简单
   * 使用方式：

     * 在 PostgreSQL 安装 `pgvector` 扩展
     * 创建带 `vector` 字段的表存文档块向量

2. **Chroma（本地向量库）**

   * 优点：LangChain 集成方便、无需修改 PostgreSQL
   * 用途：快速构建本地 RAG Demo

**架构要求：**

* 抽象一层 `VectorStoreClient`：

  ```python
  class VectorStoreClient:
      def add_documents(self, docs: list[Document]) -> None: ...
      def similarity_search(self, query: str, k: int = 5) -> list[Document]: ...
  ```
* KnowledgeService / RAG 只依赖这个抽象，不关心底层具体实现。

#### 3.4.3 缓存（Redis）

* 使用 Redis 存放：

  * 热门查询结果（今日比赛、积分榜）
  * `football-data.org` API 响应缓存（减轻调用频率）
  * 简单的 session / rate limit

* 不使用 Redis 持久化业务数据（这些写 PostgreSQL）。

---

### 3.5 外部数据源与 API

#### 3.5.1 football-data.org

* 使用 API 版本：v4（REST）

* 典型 endpoint：

  * `/v4/competitions`
  * `/v4/competitions/{id}/matches`
  * `/v4/competitions/{id}/standings`
  * `/v4/teams/{id}`

* 调用方式：

  * `src/data_pipeline/ingest_football_data.py`：

    * 定时拉取数据，写入 PostgreSQL
  * `DataService`：

    * **优先**从 PostgreSQL 读取；
    * 如无数据且允许实时请求，则调用 API，并写入 DB 作为缓存（按策略决定是否允许）。

---

### 3.6 配置管理与环境变量

* 配置文件：

  * `config/settings.py` 使用 Pydantic Settings 定义：

    * DB 连接信息
    * Redis 地址
    * LLM provider / base URL / API key
    * football-data API key
* 环境变量：

  * `SPORT_AGENT_ENV=dev|staging|prod`
  * `DATABASE_URL=...`
  * `REDIS_URL=...`
  * `LLM_PROVIDER=ollama|openai|...`
  * `FOOTBALL_DATA_API_KEY=...`

---

### 3.7 依赖版本锁定（示例）

建议在 `pyproject.toml` 或 `requirements.txt` 中固定主版本号，例如：

* `fastapi ~= 0.115`
* `uvicorn[standard] ~= 0.30`
* `langchain ~= 0.3`
* `pydantic ~= 2.8`
* `sqlalchemy ~= 2.0`
* `psycopg[binary] ~= 3.2`
* `redis ~= 5.0`
* `sentence-transformers ~= 3.0`
* `pgvector ~= 0.2`（如使用）
* `python-dotenv` 或 `pydantic-settings` 用于配置管理

## 4. 智能体整体设计（Agent System Design）

本章定义所有智能体（Supervisor + Experts）的职责边界、交互方式与实现方式，重点说明：  
LangChain 用在哪一层、每个 Agent 接口长什么样。

---

### 4.1 智能体分类与职责

系统中有两类智能体：

1. **Supervisor Agent（监督智能体）**
   - 负责：任务规划、专家调度、质量控制、最终回答生成。
   - 不负责：直接查库、直接调 HTTP、直接跑模型。

2. **Expert Agents（专家智能体）**
   - `DataStatsAgent`：数据查询 + 特征计算。
   - `PredictionAgent`：调用预测模型并结构化输出结果。
   - `KnowledgeAgent`：RAG 知识问答。
   - `RecommendationAgent`（预留）：推荐场次/球队。

每个 Expert 本质是：**一个 LangChain AgentExecutor + 一组 Tools + 一份 Prompt**。

---

### 4.2 交互关系（时序）

以“复杂问题：下轮阿森纳 vs 曼城谁更有优势？为什么？”为例，时序流程如下（伪时序图描述）：

1. `Client` → `API /api/chat` 发送 query。
2. `API` → `SupervisorAgent.run(query, session_id)`。
3. SupervisorAgent 内部使用 LLM 进行：
   - 意图识别（需要预测 + 数据 + 解释）。
   - 子任务规划（需要 DataStats → Prediction → Knowledge）。
4. SupervisorAgent 依次调用：
   - `data_stats_expert_tool(query_for_data)` → 调 `DataStatsAgent`。
   - `prediction_expert_tool(query_for_pred)` → 调 `PredictionAgent`。
   - `knowledge_expert_tool(query_for_explain)` → 调 `KnowledgeAgent`。
5. 对每个 Expert 返回结果，Supervisor 进行：
   - 结构化合并；
   - LLM 级别质量校验；
   - 生成最终自然语言回答。
6. 结果返回给 API 层 → Client。

---

### 4.3 通信模式：Expert-as-Tool

Supervisor 不直接“调 Agent”，而是通过 LangChain Tool 包裹 Expert：

- 每个 Expert 暴露一个 Tool，例如：
  - `data_stats_expert_tool`
  - `prediction_expert_tool`
  - `knowledge_expert_tool`
- 每个 Tool 内部调用对应 AgentExecutor 的 `invoke()` / `ainvoke()`。

伪代码示例：

```python
# supervisor/expert_registry.py

from langchain.tools import Tool

class ExpertRegistry:
    def __init__(self, llm_client, services):
        self.data_stats_agent = build_data_stats_agent(llm_client, services)
        self.prediction_agent = build_prediction_agent(llm_client, services)
        self.knowledge_agent = build_knowledge_agent(llm_client, services)

    def as_tools(self) -> list[Tool]:
        return [
            Tool(
                name="data_stats_expert",
                description="查询比赛、联赛、球队状态与统计特征时使用。",
                func=lambda query: self.data_stats_agent.invoke({"input": query})["output"],
            ),
            Tool(
                name="prediction_expert",
                description="对给定比赛进行胜平负预测并输出结构化结果时使用。",
                func=lambda query: self.prediction_agent.invoke({"input": query})["output"],
            ),
            Tool(
                name="knowledge_expert",
                description="解释规则、战术、比赛关键点、战术名词时使用。",
                func=lambda query: self.knowledge_agent.invoke({"input": query})["output"],
            ),
        ]
````

Supervisor Agent 的 `tools` 列表即由上述 `as_tools()` 提供。

---

## 5. 监督智能体（Supervisor Agent）

### 5.1 组件构成

SupervisorAgent 内部由四部分组成：

1. **TaskPlanner**

   * 基于 LLM + Prompt 生成子任务规划（JSON）。
2. **ExpertOrchestrator**

   * 根据子任务类型，调用对应 Expert Tool。
3. **ResultValidator**

   * 使用 LLM 对中间结果进行质量评估（是否回答了子任务、是否缺关键信息）。
4. **AnswerSynthesizer**

   * 将所有结构化结果转为自然语言回答。

---

### 5.2 接口定义

```python
# supervisor/supervisor_agent.py

class SupervisorAgent:
    def __init__(self, llm_client: LLMClient, expert_registry: ExpertRegistry, memory: ConversationMemory):
        self.llm = llm_client.as_langchain_chat_model()
        self.tools = expert_registry.as_tools()
        self.memory = memory
        self.agent_executor = build_supervisor_executor(self.llm, self.tools, self.memory)

    async def run(self, query: str, session_id: str) -> dict:
        """
        输入:
            query: 用户自然语言问题
            session_id: 会话 ID，用于 Memory 关联
        输出:
            {
              "answer": str,               # 最终自然语言回答
              "debug": { ... },            # 可选的调试信息
              "intermediate": { ... }      # 可选的中间结构化结果
            }
        """
        result = await self.agent_executor.ainvoke({"input": query, "session_id": session_id})
        return result
```

`build_supervisor_executor` 使用 LangChain `create_openai_functions_agent` 或 Runnable Graph 实现。

---

### 5.3 Prompt 结构（示意）

Supervisor 的系统提示包括：

* 它能使用哪些工具（专家）。
* 每个工具能解决哪类任务。
* 要求：

  * 先规划子任务；
  * 再按顺序用工具解决；
  * 最后合成回答时解释依据，避免瞎编。

示意（伪）：

```text
你是 Sport Agent 的监督智能体，负责调度多个专家智能体。

你可以使用以下工具：
1. data_stats_expert: 用于查询联赛、比赛、球队状态、近期表现、主客场差异等。
2. prediction_expert: 用于对一场具体比赛输出胜平负概率及相关特征说明。
3. knowledge_expert: 用于解释足球规则、战术、专业名词和比赛分析逻辑。

流程要求：
- 仔细理解用户问题。
- 规划你需要调用哪些专家以及顺序。
- 不要自己幻想数据，所有事实必须来自工具返回。
- 最终回答时，用自然语言整合工具结果，并说明依据。
```

---

### 5.4 结果验证（ResultValidator）

ResultValidator 的职责：

* 判断当前结果是否：

  * 回答了用户问题；
  * 在事实范围内；
  * 是否需要补充信息。
* 若不满意：

  * 可触发同一工具的重试（带上问题反馈）；
  * 或走降级策略（只返回已有信息，承认不确定）。

实现方式：

* 使用一个内部 LLM 调用（可与 Supervisor 共用模型）；
* Prompt 中提供：

  * 用户原始问题；
  * 工具结果；
  * 目标要求（coverage / relevance）。

---

## 6. 专家智能体（Expert Agents）

每个 Expert Agent 单独实现、单独可测试。

### 6.1 DataStatsAgent

**职责：**

* 对话中与“数据/状态/特征”相关的子问题：

  * 查询指定联赛/比赛/球队的结构化数据；
  * 计算近况、主客场、H2H 等统计特征；
* 为 PredictionAgent 提供特征，也为 Supervisor 提供可直接说的“数据事实”。

**内部组件：**

* 工具：

  * `DataTool.get_matches(...)`
  * `DataTool.get_standings(...)`
  * `StatsTool.get_team_form(...)`
  * `StatsTool.get_h2h(...)`
* 依赖 Service：

  * `DataService`
  * `StatsService`

**输入/输出示例：**

* 输入（来自 Supervisor）：

  * `"请给我阿森纳和曼城最近5场比赛的表现和进球情况"`
* 输出：

  ```json
  {
    "teams": ["Arsenal", "Manchester City"],
    "arsenal_form": {
      "last_5": ["W","W","D","L","W"],
      "goals_for": 9,
      "goals_against": 4
    },
    "city_form": {
      "last_5": ["W","L","W","W","D"],
      "goals_for": 11,
      "goals_against": 5
    },
    "head_to_head": {
      "last_5": {"arsenal_wins": 2, "city_wins": 3, "draws": 0}
    }
  }
  ```

---

### 6.2 PredictionAgent

**职责：**

* 接收一个明确的比赛（home team, away team, match context）；
* 调用 PredictService 输出胜平负概率、关键信号与基线解释。

**依赖：**

* `PredictTool`（内调 `PredictService.predict_match()`）。
* `DataStatsAgent` 提供的特征可作为前置依赖（由 Supervisor 决定调用顺序）。

**输出示例：**

```json
{
  "match": {"home": "Arsenal", "away": "Manchester City"},
  "probabilities": {
    "home_win": 0.41,
    "draw": 0.28,
    "away_win": 0.31
  },
  "confidence": 0.7,
  "key_factors": [
    "Arsenal recent home form is strong.",
    "Man City has congested schedule (3 matches in 7 days).",
    "Head-to-head slightly favors Man City."
  ]
}
```

---

### 6.3 KnowledgeAgent（RAG）

**职责：**

* 处理“规则 / 战术 / 历史知识类”问题；
* 不访问体育数据 API，不回答实时比分、预测结果；
* 只访问 RAG 知识库（规则文档 / 战术文章等）。

**依赖：**

* `KnowledgeTool`（内调 `KnowledgeService.answer()`）。

**典型问题：**

* “越位规则是什么？”
* “为什么 4-3-3 适合边路强的球队？”
* “英超和西甲在节奏上有什么差异？”

---

### 6.4 RecommendationAgent（预留）

当前仅保留接口与位置，不强制实现。

**目标能力：**

* 基于当前赛事数据与用户偏好推荐：

  * 今天适合看的三场比赛；
  * 最近值得关注的球队/球员。

**预期依赖：**

* `RecommendService`
* `DataStatsAgent` 提供的赛程与排名信息。

---

## 7. 工具层设计（LangChain Tools）

### 7.1 设计原则

* 每个 Tool 只负责一个独立的业务动作；
* 输入/输出必须是结构化（BaseModel/JSON），**避免纯字符串再让 LLM乱猜**；
* Tool 不直接操作 DB、HTTP，只调 Service；
* 所有 Tool 都有清晰的描述字符串（给 LLM 看）。

---

### 7.2 典型工具定义示例

#### 7.2.1 DataTool.get_matches

```python
# agent/tools/data_tools.py

from langchain.tools import StructuredTool
from pydantic import BaseModel

class GetMatchesInput(BaseModel):
    competition: str
    date: str | None = None
    team_name: str | None = None

def get_matches_impl(params: GetMatchesInput, data_service: DataService) -> dict:
    matches = data_service.get_matches(
        competition=params.competition,
        date=params.date,
        team_name=params.team_name
    )
    return {"matches": [m.to_dict() for m in matches]}

def build_get_matches_tool(data_service: DataService) -> StructuredTool:
    return StructuredTool.from_function(
        func=lambda **kwargs: get_matches_impl(GetMatchesInput(**kwargs), data_service),
        name="get_matches",
        description="查询指定联赛在某一天或包含指定球队的比赛列表。",
    )
```

其他工具（StatsTool / PredictTool / KnowledgeTool）类似。

---

### 7.3 错误处理约定

* Tool 内部 Service 抛出的异常应转换为：

  * 结构化错误信息（例如 `{"error": "NOT_FOUND", "message": "team not found"}`）
* LLM 在看到错误结构时：

  * 可以请求澄清（“请问你指的是阿森纳还是阿森纳女足？”）
  * 或告知用户无法完成请求。

---

## 8. 服务层设计（Service Layer）

### 8.1 DataService

**职责：**

* 封装所有与比赛 / 球队 / 联赛相关的数据访问；
* 统一处理：

  * 名称映射（别名 → 标准 ID）；
  * 本地 DB 查询；
  * 必要时调用 football-data API 回源。

**示意接口：**

```python
class DataService:
    def get_competitions(self) -> list[Competition]: ...
    def get_team(self, team_name_or_id: str) -> Team: ...
    def get_matches(self, competition: str, date: str | None, team_name: str | None) -> list[Match]: ...
    def get_standings(self, competition: str) -> StandingTable: ...
```

---

### 8.2 StatsService

**职责：**

* 聚合 DataService 提供的数据，输出统计特征；
* 不直接访问外部 API / DB。

**示意接口：**

```python
class StatsService:
    def get_team_form(self, team_id: int, last_n: int = 5) -> TeamFormStats: ...
    def get_home_away_stats(self, team_id: int, last_n: int = 10) -> HomeAwayStats: ...
    def get_head_to_head(self, team_a_id: int, team_b_id: int, last_n: int = 5) -> HeadToHeadStats: ...
    def get_schedule_density(self, team_id: int, window_days: int = 7) -> ScheduleDensity: ...
```

---

### 8.3 PredictService

**职责：**

* 聚合 StatsService 特征；
* 调用预测模型（规则 + 机器学习）；
* 输出胜平负概率与解释。

**示意接口：**

```python
class PredictService:
    def predict_match(self, match_id: int) -> PredictionResult: ...
    def predict_match_by_teams(self, home_team_id: int, away_team_id: int, competition_id: int, match_date: date) -> PredictionResult: ...
```

`PredictionResult` 包含：

* `home_win / draw / away_win`
* `confidence`（基于模型校准）
* `feature_contributions`（解释用）

---

### 8.4 KnowledgeService（RAG）

**职责：**

* 管理完整 RAG pipeline：

  * 文本加载 → 切分 → 向量化 → 存储 → 检索 → 调 LLM 生成回答；
* 接收自然语言 query，返回自然语言 answer（内部可使用结构化中间态）。

**示意接口：**

```python
class KnowledgeService:
    def __init__(self, vector_store_client: VectorStoreClient, llm_client: LLMClient):
        ...

    def answer(self, query: str, lang: str = "zh") -> str:
        ...
```

---

### 8.5 RecommendService（预留）

接口示例：

```python
class RecommendService:
    def recommend_matches(self, date: date, user_profile: UserProfile | None = None, top_k: int = 3) -> list[RecommendedMatch]: ...
```

---

## 9. 数据设计与存储（Data & Storage）

这里只写关键信息，详细表结构可以在单独 DDL 文档中展开。

### 9.1 主要实体

* `competitions`（联赛）
* `teams`
* `matches`
* `standings`
* `team_stats_agg`（可选预计算表）
* `rag_documents`（非结构化知识原文索引）

---

### 9.2 PostgreSQL 示例建模（简化）

```sql
CREATE TABLE competitions (
    id          SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE,
    code        VARCHAR(10),
    name        VARCHAR(100),
    country     VARCHAR(50)
);

CREATE TABLE teams (
    id          SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE,
    name        VARCHAR(100),
    short_name  VARCHAR(50),
    tla         VARCHAR(10),   -- 三字缩写
    competition_id INT REFERENCES competitions(id)
);

CREATE TABLE matches (
    id              SERIAL PRIMARY KEY,
    external_id     VARCHAR(50) UNIQUE,
    competition_id  INT REFERENCES competitions(id),
    season          VARCHAR(20),
    match_date      TIMESTAMP,
    status          VARCHAR(20),
    home_team_id    INT REFERENCES teams(id),
    away_team_id    INT REFERENCES teams(id),
    home_score      INT,
    away_score      INT
);

CREATE INDEX idx_matches_competition_date ON matches(competition_id, match_date);
CREATE INDEX idx_matches_home_away ON matches(home_team_id, away_team_id);
```

---

### 9.3 向量存储

若使用 pgvector：

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_chunks (
    id          SERIAL PRIMARY KEY,
    doc_id      INT,
    chunk_index INT,
    content     TEXT,
    embedding   VECTOR(768)
);

CREATE INDEX idx_rag_embedding ON rag_chunks USING ivfflat (embedding vector_cosine_ops);
```

---

### 9.4 Redis 使用

* Key 命名建议：

  * `cache:standings:{competition_code}`
  * `cache:matches:{competition_code}:{date}`
  * `session:{session_id}`（如需要）
* TTL：

  * 缓存数据：1 小时或 1 天（根据业务）
  * Session：按业务需要（例如 30 分钟无交互失效）

---

## 10. 数据管道（Data Pipeline）

### 10.1 任务定义

* **全量初始化：**

  * 抓取指定联赛（如英超）当前赛季的所有比赛数据；
  * 写入 `competitions / teams / matches / standings`。

* **增量更新：**

  * 定时（例如每小时 / 每天）拉取新增或更新的比赛；
  * 更新比分与状态；
  * 更新积分表。

---

### 10.2 实现组件

* `src/data_pipeline/ingest_football_data.py`

  * `sync_competitions()`
  * `sync_teams(competition)`
  * `sync_matches(competition, date_range)`
  * `sync_standings(competition)`

使用 `requests` 或 `httpx` 调 football-data API。

---

## 11. 预测系统（Prediction System）

### 11.1 Baseline 方案

* **规则 + Elo**：

  * 初始 Elo 通过历史结果拟合；
  * 比赛后根据结果更新评分；
  * 根据 Elo 差值映射胜平负概率（logistic）。

* **特征：**

  * Elo 差值；
  * 近况（近 N 场胜率）；
  * 主客场 dummy 变量；
  * 赛程密度（疲劳）；

后续可以引入 XGBoost / LightGBM 替代规则映射部分。

---

### 11.2 与 Agent 集成

* `PredictionAgent` 不直接触碰模型，只做：

  * 解析 Supervisor 提供的 match 信息；
  * 调用 `PredictService.predict_match_by_teams(...)`;
  * 整理输出为结构化 JSON；
* `Supervisor` 决定何时调用预测（结合用户问题与上下文）。

---

## 12. RAG 知识系统设计（Knowledge RAG）

### 12.1 语料来源与结构

* 本地 Markdown 文档：

  * `rules.md`（规则）
  * `tactics.md`（战术）
  * `league_info.md`（各联赛简介）

目录：`data/knowledge_base/*.md`

---

### 12.2 RAG Pipeline

`knowledge/rag_chain.py`：

* Loader：读取本地 md/txt；
* Splitter：按段落 / 标题切分（Chunk size ~ 500 tokens）；
* Embeddings：`bge-m3` 等；
* VectorStore：pgvector/Chroma；
* Retriever：基于 cosine / dot-product，top-k = 5~10；
* LLM 生成：调用 LLM 用 prompt 将检索结果重写成回答。

---

### 12.3 KnowledgeAgent 调用逻辑

* 对于规则类问题，直接走 RAG；
* 若问题混合比赛数据与规则（比如“这场点球是否合理？”），由 Supervisor 决定是否先用 DataStats 再用 Knowledge 补充解释。

---

## 13. 对话系统与上下文管理

### 13.1 Memory 策略

使用 LangChain Memory 对象：

* `ConversationBufferMemory` 或 `ConversationSummaryMemory`；
* key 使用 `session_id` 关联。

存储内容：

* 最近若干轮 user/assistant 消息；
* 不存敏感数据（不存用户身份信息）。

---

### 13.2 澄清与纠错

* 当 Tool 返回错误结构（如 team not found），Supervisor 可：

  * 触发 Clarification 回合，请用户确认队名；
* 通过 Prompt 要求 Supervisor 不要猜测球队名称。

---

## 14. 推荐系统（Future）

暂留部分，只定义接口与基本逻辑，不展开。

---

## 15. 外部接口（API Spec）概览

（详细可单独写 `API_SPEC.md`）

* `POST /api/chat`
* `GET /api/match`
* `GET /api/standing`
* `GET /api/team`

---

## 16. 部署与监控（简要）

* 部署形态：

  * FastAPI + Uvicorn
  * LLM 推理服务（Ollama/vLLM）单独进程或容器
  * PostgreSQL + Redis（独立服务）
* 监控：

  * 记录每次 /api/chat 的：

    * 耗时
    * 调用的 Tools/Agents 链路
    * 错误信息

---

## 17. 安全与权限（Skeleton）

* API Key 校验（内网可简化）
* IP 限流
* 日志脱敏

---

## 18. 测试策略（Skeleton）

* 单元测试：

  * Service 层
  * 工具层（用 fake services）
* 集成测试：

  * 起一个本地 LLM stub
  * 测试 Supervisor + Experts 的完整链路

---

## 19. 扩展规范（新增能力）

新增任何能力的标准流程：

1. 在 Service 层实现业务逻辑；
2. 用 LangChain Tool 封装该 Service；
3. 如有必要，增加新的 Expert Agent；
4. 更新 `ExpertRegistry` 注册该工具/专家；
5. 更新 Supervisor Prompt，描述新能力。

---

## 20. 目录结构（建议）

```text
src/
  api/
    routes/
      chat.py
      data.py
  supervisor/
    supervisor_agent.py
    expert_registry.py
  agent/
    data_stats_agent.py
    prediction_agent.py
    knowledge_agent.py
    tools/
      data_tools.py
      stats_tools.py
      predict_tools.py
      knowledge_tools.py
  services/
    data_service.py
    stats_service.py
    predict_service.py
    knowledge_service.py
  knowledge/
    loader.py
    splitter.py
    embeddings.py
    vectorstore_client.py
    rag_chain.py
  shared/
    llm_client.py
    config.py
    logging.py
  data_pipeline/
    ingest_football_data.py
  infra/
    db.py
    redis.py
    models.py
docs/
  TECH_SPEC.md
  API_SPEC.md
  RAG_DESIGN.md
data/
  knowledge_base/
    rules.md
    tactics.md
    league_info.md
```

```



