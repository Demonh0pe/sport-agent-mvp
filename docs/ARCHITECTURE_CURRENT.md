# Sport Agent V3 当前架构详解

## 一、上下文记忆状态

### 当前实现

**是否有记忆：预留了接口，但未完全实现**

```python
# src/supervisor/supervisor_agent.py
def __init__(self, enable_memory: bool = True):
    self._enable_memory = enable_memory  # 参数已预留
    # 但实际的 memory 实现需要补充
```

**现状**：
- [完成] 参数已预留：`enable_memory=True`
- [待实现] 实际记忆存储：未实现
- [待实现] 会话上下文：未持久化
- [待实现] 多轮对话：当前每次调用独立

**影响**：
- 每次对话都是新会话
- Agent 不记得之前的对话内容
- 无法进行"那利物浦呢？"这样的追问

---

### 如何添加记忆（TODO）

#### 方案1：使用 LangChain ConversationBufferMemory

```python
from langchain.memory import ConversationBufferMemory

class SupervisorAgent:
    def _create_agent_executor(self):
        if self._enable_memory:
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        else:
            memory = None
        
        return AgentExecutor(
            agent=agent,
            tools=self._expert_tools,
            memory=memory,  # 添加记忆
            verbose=True
        )
```

#### 方案2：使用 Redis 持久化会话

```python
from langchain.memory import RedisChatMessageHistory

class SupervisorAgent:
    def _create_session_memory(self, session_id: str):
        """根据 session_id 创建独立记忆"""
        message_history = RedisChatMessageHistory(
            session_id=session_id,
            url="redis://localhost:6379/0"
        )
        
        return ConversationBufferMemory(
            chat_memory=message_history,
            memory_key="chat_history",
            return_messages=True
        )
```

---

## 二、当前 Agent 架构

### 整体架构图

```
用户查询
    ↓
AgentServiceV3 (统一入口)
    ↓
SupervisorAgent (监督智能体)
├── 理解用户意图
├── 规划任务步骤
├── 调度 Expert Agents (通过 Tools)
└── 合成最终答案
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ DataStatsAgent  │ PredictionAgent │ KnowledgeAgent  │
│ (数据统计)      │ (比赛预测)      │ (知识问答)      │
│ [已实现]        │ [已实现]        │ [待实现]        │
└─────────────────┴─────────────────┴─────────────────┘
    ↓
Service 层 (纯 Python，无 LLM 依赖)
├── DataService (数据访问)
├── StatsService (统计计算)
└── PredictService (预测逻辑)
    ↓
数据层 (PostgreSQL + API)
```

---

### 核心组件详解

#### 1. SupervisorAgent（监督智能体）

**文件**：`src/supervisor/supervisor_agent.py`

**职责**：
- 理解用户意图
- 规划任务步骤
- 调度 Expert Agents
- 验证结果完整性
- 合成最终答案

**关键代码**：
```python
class SupervisorAgent:
    def __init__(self, expert_tools, llm_client_instance, enable_memory=True):
        self._expert_tools = expert_tools  # 专家工具列表
        self._llm = llm_client.as_langchain_chat_model()
        self._agent_executor = self._create_agent_executor()
    
    async def run(self, query: str, session_id=None, context=None):
        """处理用户查询"""
        result = await self._agent_executor.ainvoke({
            "input": query,
            "session_id": session_id or "default"
        })
        return result
```

**特点**：
- 基于 LangChain AgentExecutor
- 使用 ChatPromptTemplate 定义 System Prompt
- 自动选择和调用 Expert Tools

---

#### 2. ExpertRegistry（专家注册表）

**文件**：`src/supervisor/expert_registry.py`

**职责**：
- 注册所有 Expert Agents
- 将 Agents 封装为 LangChain Tools
- 提供给 Supervisor 使用

**当前注册的 Experts**：
```python
def _initialize_experts(self):
    from src.agent.data_stats_agent import DataStatsAgent
    from src.agent.prediction_agent import PredictionAgent
    # from src.agent.knowledge_agent import KnowledgeAgent  # 待实现
    
    self._experts["data_stats"] = DataStatsAgent(self._llm_client)
    self._experts["prediction"] = PredictionAgent(self._llm_client)
    # self._experts["knowledge"] = KnowledgeAgent(self._llm_client)
```

**Expert → Tool 转换**：
```python
def as_tools(self) -> List[Tool]:
    tools = []
    
    # DataStatsAgent → data_stats_expert Tool
    tools.append(Tool(
        name="data_stats_expert",
        description="查询比赛、联赛、球队状态...",
        func=self._create_expert_caller("data_stats"),
        coroutine=self._create_expert_caller_async("data_stats")
    ))
    
    # PredictionAgent → prediction_expert Tool
    tools.append(Tool(
        name="prediction_expert",
        description="预测比赛胜负...",
        func=self._create_expert_caller("prediction"),
        coroutine=self._create_expert_caller_async("prediction")
    ))
    
    return tools
```

---

#### 3. Expert Agents（专家智能体）

##### DataStatsAgent（数据统计专家）

**文件**：`src/agent/data_stats_agent.py`

**职责**：
- 查询比赛数据
- 查询球队状态
- 查询积分榜
- 计算统计特征

**依赖的 Service**：
- DataService（数据访问）
- StatsService（统计计算）

**示例场景**：
```
用户: "曼联最近5场比赛战绩如何？"
  ↓
Supervisor 调用 data_stats_expert
  ↓
DataStatsAgent.run("曼联最近5场比赛战绩如何？")
  ↓
DataService.get_recent_matches("曼联", 5)
  ↓
返回：战绩数据 + 自然语言描述
```

---

##### PredictionAgent（预测专家）

**文件**：`src/agent/prediction_agent.py`

**职责**：
- 预测比赛结果
- 计算胜平负概率
- 分析关键影响因素

**依赖的 Service**：
- DataService（获取球队数据）
- PredictService（预测逻辑）

**示例场景**：
```
用户: "阿森纳对曼城谁会赢？"
  ↓
Supervisor 调用 prediction_expert
  ↓
PredictionAgent.run("阿森纳对曼城谁会赢？")
  ↓
PredictService.predict_match("阿森纳", "曼城")
  ↓
返回：概率分布 + 关键因素 + 自然语言解释
```

---

##### KnowledgeAgent（知识专家）- 待实现

**状态**：已在代码中预留，但未实现

**计划职责**：
- 解释足球规则
- 解释战术体系
- 回答足球历史问题

**依赖系统**：
- RAG (Retrieval-Augmented Generation)
- VectorStore（pgvector 或 Chroma）
- 足球知识库

---

#### 4. Service 层（纯 Python）

**设计原则**：
- 不依赖 LangChain
- 不依赖 LLM
- 可独立测试
- 可被其他系统复用

**核心 Services**：

```python
# src/services/data_service.py
class DataService:
    async def get_team(self, team_name: str) -> Team
    async def get_recent_matches(self, team_name: str, last_n: int) -> List[Match]
    async def get_standings(self, league_name: str) -> List[Standing]
    async def get_h2h(self, team1: str, team2: str) -> List[Match]

# src/services/stats_service.py
class StatsService:
    async def calculate_team_form(self, team_id: str, last_n: int) -> dict
    async def calculate_h2h_stats(self, team1_id: str, team2_id: str) -> dict
    async def calculate_venue_performance(self, team_id: str) -> dict

# src/services/predict_service.py
class PredictService:
    async def predict_match(self, home_team: str, away_team: str) -> dict
    async def explain_prediction(self, prediction: dict) -> str
```

---

## 三、如何添加新 Agent

### 步骤详解

#### 步骤1：创建 Expert Agent 类

**文件位置**：`src/agent/your_new_agent.py`

**模板**：

```python
"""
YourNewAgent - 你的新专家智能体

职责：
- 描述这个 Agent 的职责
- 它解决什么类型的问题
"""
import logging
from typing import Dict, Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class YourNewAgent:
    """你的新专家智能体"""
    
    def __init__(self, llm_client):
        """
        初始化 Agent
        
        Args:
            llm_client: LLM 客户端实例
        """
        self._llm_client = llm_client
        self._llm = llm_client.as_langchain_chat_model()
        
        # 如果需要依赖 Service 层
        from src.services.your_service import YourService
        self._service = YourService()
        
        # 创建 Agent Executor
        self._agent_executor = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        """创建 LangChain Agent"""
        
        # 定义 System Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是 {专家名称}，专门处理 {专业领域} 相关问题。
            
你的职责：
1. {职责1}
2. {职责2}
3. {职责3}

工作流程：
1. 分析用户问题
2. 调用相关工具/Service
3. 返回结构化结果
"""),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        # 如果需要定义工具
        from langchain.tools import Tool
        tools = [
            Tool(
                name="your_tool_name",
                description="工具描述",
                func=self._your_function
            )
        ]
        
        # 创建 Agent
        agent = create_react_agent(
            llm=self._llm,
            tools=tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=5
        )
    
    def _your_function(self, query: str) -> str:
        """你的业务逻辑"""
        # 调用 Service 层
        result = self._service.do_something(query)
        return str(result)
    
    def run(self, query: str) -> str:
        """
        同步运行（供 LangChain Tool 调用）
        
        Args:
            query: 用户查询
            
        Returns:
            自然语言回答
        """
        try:
            result = self._agent_executor.invoke({"input": query})
            return result.get("output", "无法处理该问题")
        except Exception as e:
            logger.error(f"YourNewAgent.run failed: {e}")
            return f"处理问题时出错：{str(e)}"
    
    async def arun(self, query: str) -> str:
        """
        异步运行（供 LangChain Tool 异步调用）
        
        Args:
            query: 用户查询
            
        Returns:
            自然语言回答
        """
        try:
            result = await self._agent_executor.ainvoke({"input": query})
            return result.get("output", "无法处理该问题")
        except Exception as e:
            logger.error(f"YourNewAgent.arun failed: {e}")
            return f"处理问题时出错：{str(e)}"
```

---

#### 步骤2：在 ExpertRegistry 中注册

**文件**：`src/supervisor/expert_registry.py`

**修改位置1**：导入新 Agent

```python
def _initialize_experts(self):
    """初始化所有 Expert Agents"""
    logger.info("Initializing Expert Agents...")
    
    try:
        # 导入现有 Agents
        from src.agent.data_stats_agent import DataStatsAgent
        from src.agent.prediction_agent import PredictionAgent
        
        # 导入你的新 Agent
        from src.agent.your_new_agent import YourNewAgent
        
        # 实例化 Experts
        self._experts["data_stats"] = DataStatsAgent(self._llm_client)
        self._experts["prediction"] = PredictionAgent(self._llm_client)
        
        # 实例化你的新 Agent
        self._experts["your_new"] = YourNewAgent(self._llm_client)
        
        logger.info(f"Successfully initialized {len(self._experts)} experts")
```

**修改位置2**：注册为 Tool

```python
def as_tools(self) -> List[Tool]:
    """将所有 Expert Agents 转换为 LangChain Tools"""
    tools = []
    
    # ... 现有 Tools ...
    
    # YourNewAgent → Tool
    if "your_new" in self._experts:
        tools.append(
            Tool(
                name="your_new_expert",  # Tool 名称（Supervisor 会看到）
                description=(
                    "处理 {具体场景} 时使用。"
                    "适用场景："
                    "- {场景1}"
                    "- {场景2}"
                    "- {场景3}"
                    "输入：自然语言查询"
                    "输出：结构化结果或自然语言描述"
                ),
                func=self._create_expert_caller("your_new"),
                coroutine=self._create_expert_caller_async("your_new")
            )
        )
    
    logger.info(f"Registered {len(tools)} expert tools")
    return tools
```

---

#### 步骤3：更新 Supervisor Prompt

**文件**：`src/supervisor/supervisor_agent.py`

**修改位置**：`_create_supervisor_prompt()` 方法

```python
def _create_supervisor_prompt(self) -> ChatPromptTemplate:
    system_message = """你是 Sport Agent 的监督智能体...

你可以使用以下专家工具：

1. **data_stats_expert**: 查询数据和统计...
2. **prediction_expert**: 预测比赛结果...
3. **your_new_expert**: {描述你的新 Expert 的用途}
   - 适用场景：{场景1}
   - 适用场景：{场景2}

**工作流程要求**：
...（保持原有逻辑，添加新 Expert 的调用时机）
"""
```

---

#### 步骤4：测试新 Agent

**创建测试文件**：`scripts/test_your_new_agent.py`

```python
import asyncio
from src.services.agent_service_v3 import ask_expert

async def test_new_agent():
    # 直接测试新 Agent
    result = await ask_expert("your_new", "测试问题")
    print(f"结果: {result}")
    
    # 通过 Supervisor 测试（自动调度）
    from src.services.agent_service_v3 import ask
    result = await ask("触发新 Agent 的问题")
    print(f"Supervisor 调度结果: {result}")

asyncio.run(test_new_agent())
```

---

### 完整示例：添加 RecommendationAgent

假设我们要添加一个推荐专家，推荐用户看哪场比赛。

#### 1. 创建 Agent

**文件**：`src/agent/recommendation_agent.py`

```python
class RecommendationAgent:
    """比赛推荐专家"""
    
    def __init__(self, llm_client):
        self._llm_client = llm_client
        self._llm = llm_client.as_langchain_chat_model()
        
        from src.services.data_service import data_service
        from src.services.predict_service import predict_service
        self._data_service = data_service
        self._predict_service = predict_service
    
    async def arun(self, query: str) -> str:
        """推荐精彩比赛"""
        # 1. 获取未来比赛
        upcoming = await self._data_service.get_upcoming_matches(days=7)
        
        # 2. 评分（根据球队实力、排名接近度等）
        scored_matches = []
        for match in upcoming:
            prediction = await self._predict_service.predict_match(
                match.home_team_name, 
                match.away_team_name
            )
            
            # 评分逻辑：越接近50%越精彩
            excitement = 1 - abs(0.5 - prediction['home_win_prob'])
            scored_matches.append((match, excitement, prediction))
        
        # 3. 排序并推荐 Top 3
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        top_3 = scored_matches[:3]
        
        # 4. 生成推荐文本
        recommendations = []
        for match, score, pred in top_3:
            rec = f"""
{match.home_team_name} vs {match.away_team_name}
时间：{match.match_date}
精彩度：{score:.1%}
预测：主胜 {pred['home_win_prob']:.0%}, 平局 {pred['draw_prob']:.0%}, 客胜 {pred['away_win_prob']:.0%}
"""
            recommendations.append(rec)
        
        return "\n".join(recommendations)
```

#### 2. 注册

在 `ExpertRegistry` 中：

```python
from src.agent.recommendation_agent import RecommendationAgent

self._experts["recommendation"] = RecommendationAgent(self._llm_client)

tools.append(Tool(
    name="recommendation_expert",
    description="推荐精彩比赛时使用。适用场景：用户询问'有什么好看的比赛'、'推荐一场比赛'等",
    func=self._create_expert_caller("recommendation"),
    coroutine=self._create_expert_caller_async("recommendation")
))
```

#### 3. 更新 Prompt

在 Supervisor 的 System Prompt 中：

```python
4. **recommendation_expert**: 推荐精彩比赛
   - 适用场景：用户询问"有什么好看的比赛"、"推荐一场比赛"
```

#### 4. 测试

```bash
python scripts/chat_interactive.py
```

```
你: 有什么精彩的比赛推荐吗？

Agent: 正在处理...
------------------------------------------------------------

为你推荐以下精彩比赛：

1. 曼联 vs 利物浦
   时间：2024-12-01 20:00
   精彩度：95%
   预测：主胜 48%, 平局 27%, 客胜 25%

2. 阿森纳 vs 曼城
   时间：2024-12-02 18:30
   精彩度：92%
   预测：主胜 45%, 平局 30%, 客胜 25%

...
```

---

## 四、架构优势

### 1. 模块化

- 每个 Agent 独立实现
- Service 层可复用
- 易于单元测试

### 2. 可扩展

- 添加新 Agent 只需3步
- 不影响现有 Agents
- Supervisor 自动学会使用新 Agent

### 3. 分层清晰

```
Agent 层（LangChain）- 智能调度和推理
    ↓
Service 层（纯 Python）- 业务逻辑
    ↓
Data 层（PostgreSQL）- 数据存储
```

### 4. 易于维护

- 每个组件职责单一
- 代码结构清晰
- 文档完善

---

## 五、下一步优化建议

### 1. 实现会话记忆

**优先级**：高

**步骤**：
1. 添加 Redis 支持
2. 实现 ConversationBufferMemory
3. 支持 session_id 管理
4. 测试多轮对话

### 2. 完成 KnowledgeAgent

**优先级**：中

**步骤**：
1. 搭建 RAG 系统
2. 准备足球知识库
3. 实现 VectorStore
4. 集成到 KnowledgeAgent

### 3. 优化 Tool 调用

**优先级**：中

**改进**：
- 使用 StructuredTool（类型安全）
- 定义 Pydantic Schema
- 更精确的 Tool Description

### 4. 添加监控和日志

**优先级**：低

**功能**：
- 记录每次 Agent 调用
- 统计 Tool 使用频率
- 分析响应时间

---

## 六、相关文档

- **技术规范**：`docs/SportAgent_TechSpec_v2_FULL.md`
- **快速启动**：`QUICK_START.md`
- **聊天指南**：`CHAT_GUIDE.md`
- **项目状态**：`PROJECT_STATUS.md`

---

**更新日期**：2025-11-27  
**架构版本**：V3.1.3

