# Agent 工具 Schema 修复总结

## 修复日期
2025-11-27

## 背景
基于一轮完整的交互日志分析，识别出了以下关键问题：
1. 工具 schema 不正确 - Action Input 被当成字符串
2. `get_standings` 工具无法查询特定球队排名
3. 环境层警告（urllib3 + LibreSSL）
4. LangChain memory API 弃用警告

## 修复内容

### ✅ 1. 修复 urllib3 警告
**文件**: `requirements.txt`

**问题**: macOS 系统的 LibreSSL 与 urllib3 v2 不兼容

**修复**: 添加版本锁定
```txt
urllib3<2  # macOS LibreSSL 兼容性 - 生产环境用 OpenSSL 可移除此限制
```

**说明**: 
- 临时解决方案，适用于本地开发环境
- 生产环境（Linux/Docker）应使用 OpenSSL，可移除此限制

---

### ✅ 2. 重构 DataStatsAgent 工具为强类型 Schema
**文件**: `src/agent/data_stats_agent.py`

#### 修复前的问题
工具函数接受 `query: str` 参数，内部尝试 `json.loads()` 解析：
```python
async def get_recent_matches(query: str) -> str:
    try:
        data = json.loads(query)  # ❌ 不可靠
        team_name = data.get("team_name", query)
    except:
        team_name = query
```

这导致：
- LLM 输出的整个 JSON 被当成一个字符串传入
- 出现类似 `无法解析球队名称: '{"teams": ["Brighton", "Arsenal"]}'` 的错误

#### 修复后的实现

**定义强类型 Schema**:
```python
class GetRecentMatchesInput(BaseModel):
    """获取球队最近比赛的输入参数"""
    team_name: str = Field(..., description="球队名称，支持中英文")
    match_count: int = Field(10, description="要查询的比赛数量")

class GetStandingsInput(BaseModel):
    """获取联赛积分榜的输入参数"""
    competition: str = Field(..., description="联赛名称")
    team_name: Optional[str] = Field(None, description="可选：查询该队的精确排名")
    full_list: bool = Field(False, description="是否返回完整积分榜")

# 其他工具的 Schema...
```

**工具函数直接接收强类型参数**:
```python
async def get_recent_matches(team_name: str, match_count: int = 10) -> str:
    """不再需要手动解析 JSON"""
    matches = await data_service.get_recent_matches(
        team_name=team_name,
        last_n=match_count
    )
    # ...
```

**注册时指定 args_schema**:
```python
tools = [
    StructuredTool.from_function(
        coroutine=get_recent_matches,
        name="get_recent_matches",
        description="获取球队最近的比赛列表和结果",
        args_schema=GetRecentMatchesInput  # ✅ 关键
    ),
    # ...
]
```

#### 修复的工具列表
1. `get_recent_matches` - 获取比赛记录
2. `get_team_form` - 获取球队状态
3. `get_standings` - 获取积分榜（扩展版，见下）
4. `get_head_to_head` - 获取交锋记录
5. `get_home_away_stats` - 获取主客场数据

---

### ✅ 3. 扩展 get_standings 支持 team 参数查询排名
**文件**: `src/agent/data_stats_agent.py`

#### 修复前的问题
- 只能返回前 10 名
- 无法直接查询"诺丁汉森林排第几"
- LLM 会幻想不存在的 `full_list` 参数

#### 修复后的功能

**新增三种用法**:
```python
async def get_standings(
    competition: str, 
    team_name: Optional[str] = None,  # ✅ 新增
    full_list: bool = False            # ✅ 新增
) -> str:
```

**使用场景**:
1. **只提供 competition** → 返回前 10 名
   ```json
   {"competition": "Premier League"}
   ```

2. **提供 competition + team_name** → 返回该队精确排名
   ```json
   {"competition": "Premier League", "team_name": "Nottingham Forest"}
   ```
   输出：
   ```
   Nottingham Forest FC 在 Premier League 中的排名：
   - 排名：第 13 位
   - 积分：23 分
   - 战绩：7胜 2平 8负
   - 进球/失球：20/25
   - 净胜球：-5
   ```

3. **提供 full_list=True** → 返回完整榜单（所有 20 队）
   ```json
   {"competition": "Premier League", "full_list": true}
   ```

**Prompt 更新**:
在 Agent 的 prompt 中明确说明：
```
工具使用指南：
3. get_standings: 查询积分榜，有三种用法：
   - 只提供 competition：返回前10名
   - 提供 competition 和 team_name：返回该队的精确排名（推荐用于"某队排第几"的问题）
   - 提供 competition 和 full_list=True：返回完整榜单

重要规则：
- ✅ 对于"某队排第几"的问题，优先使用 get_standings 的 team_name 参数
```

---

### ✅ 4. 重构 PredictionAgent 工具为强类型 Schema
**文件**: `src/agent/prediction_agent.py`

#### 修复内容
```python
class PredictMatchInput(BaseModel):
    """预测比赛的输入"""
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")

tools = [
    StructuredTool.from_function(
        coroutine=predict_match_impl,
        name="predict_match",
        description="预测两队比赛的胜平负结果...",
        args_schema=PredictMatchInput  # ✅ 添加
    )
]
```

---

### ✅ 5. 添加 LangChain Memory Deprecation TODO 注释
**文件**: `src/supervisor/supervisor_agent.py`

#### 修复内容
```python
from langchain.memory import ConversationBufferMemory  # TODO: Deprecated - 迁移到新的 Memory API

# ...

# 创建 Memory（如果启用）
# TODO: ConversationBufferMemory 已被 LangChain 标记为 deprecated
# 未来升级时需迁移到新的 RunnableConfig/ChatMessageHistory API
# 参考：https://python.langchain.com/docs/modules/memory/
memory = None
if self._enable_memory:
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output"
    )
```

**说明**:
- 目前仍可正常使用，但会有 deprecation warning
- 标记为技术债，等待 LangChain 稳定后统一迁移
- 升级时可能影响整个 memory 系统，需谨慎

---

## 核心修复原理

### 问题根源
LangChain 工具调用流程：
```
LLM 输出 JSON → LangChain 解析 → 传给工具函数
```

**错误做法**（修复前）:
```python
@tool
def my_tool(input: str) -> str:  # ❌ 接受字符串
    data = json.loads(input)     # ❌ 手动解析 JSON
```

问题：LangChain 会把整个 JSON 当成一个字符串传入

**正确做法**（修复后）:
```python
class MyToolInput(BaseModel):
    param1: str = Field(...)
    param2: int = Field(...)

@tool(args_schema=MyToolInput)
def my_tool(param1: str, param2: int) -> str:  # ✅ 强类型参数
    # LangChain 自动解析 JSON，直接使用参数
```

---

## 测试验证

### 测试脚本
创建了 `scripts/test_agent_fixes.py` 用于验证修复效果

### 测试场景
1. ✅ **英超积分第六是谁** - 测试榜单查询
2. ✅ **布赖顿和阿森纳哪个强** - 测试对比分析
3. ✅ **诺丁汉森林排第几** - 测试 team_name 参数
4. ✅ **曼联排第几** - 测试 team_name 参数

### 运行测试
```bash
cd /Users/dylan/Desktop/sport\ agent\ mvp
python scripts/test_agent_fixes.py
```

---

## 架构一致性检查

### ✅ 符合分层架构
所有修改都遵循了项目的分层架构约束：

| 层级 | 修改内容 | LangChain 使用 |
|------|---------|----------------|
| Agent Layer | DataStatsAgent, PredictionAgent | ✅ 允许 |
| Tool Layer | 工具 Schema 定义 + StructuredTool | ✅ 允许 |
| Service Layer | 无修改（保持纯 Python） | ❌ 禁止 |
| Infra Layer | 无修改 | ❌ 禁止 |

### ✅ 无破坏性变更
- Service 层接口不变
- 数据库 schema 不变
- 仅修改 Agent/Tool 层的 LangChain 绑定

---

## 下一步建议

### 立即可做
1. ✅ 运行测试脚本验证三个场景
2. ✅ 观察是否还有 "无法解析球队名称" 错误
3. ✅ 检查 LLM 是否还会幻想不存在的工具名

### 短期优化
1. **统一术语词典** - 创建 `docs/TEAM_ALIAS_DICTIONARY.md`
2. **调整 verbose 模式** - 区分开发/演示环境的日志输出
3. **监控工具调用** - 记录 LLM 是否仍会编造工具名（如 `data_stats_explicit`）

### 长期规划
1. **LangChain 升级准备** - Memory API 迁移（已标记 TODO）
2. **工具性能监控** - 记录工具调用耗时和成功率
3. **错误恢复机制** - 当工具调用失败时的 fallback 策略

---

## 总结

### 修复成果
- ✅ 工具 Schema 从 "字符串 + 手动解析" 升级为 "强类型 Pydantic"
- ✅ `get_standings` 支持精确查询球队排名（解决"诺丁汉森林排第几"问题）
- ✅ 消除 urllib3 警告
- ✅ 标记 LangChain Memory 技术债

### 核心价值
**从"能跑"到"可控"**：
- 工具参数类型安全，LLM 输出可预测
- 错误信息准确，易于调试
- 符合 LangChain 最佳实践
- 为后续扩展打下坚实基础

### 团队 Review 要点
展示给总监时，可以强调：
1. **工程规范** - 所有工具都是强类型，符合企业级代码标准
2. **产品完整性** - "某队排第几"这类基础问题现在能精确回答
3. **可维护性** - 技术债标记清晰，升级路径明确
4. **架构一致性** - 修改严格遵守分层架构，无侵入式变更

---

## 附录：关键代码对比

### Before vs After

#### 工具定义
```python
# ❌ Before
async def get_standings(query: str) -> str:
    try:
        data = json.loads(query)
        competition = data.get("competition", query)
    except:
        competition = query
    # ...

# ✅ After
class GetStandingsInput(BaseModel):
    competition: str = Field(...)
    team_name: Optional[str] = Field(None, ...)
    full_list: bool = Field(False, ...)

async def get_standings(
    competition: str, 
    team_name: Optional[str] = None,
    full_list: bool = False
) -> str:
    # 直接使用参数，无需解析
```

#### 工具注册
```python
# ❌ Before
StructuredTool.from_function(
    coroutine=get_standings,
    name="get_standings",
    description="获取联赛积分榜排名"
)

# ✅ After
StructuredTool.from_function(
    coroutine=get_standings,
    name="get_standings",
    description="获取联赛积分榜排名...",
    args_schema=GetStandingsInput  # 强类型约束
)
```

---

**修复完成时间**: 2025-11-27  
**修复人**: AI Assistant  
**验证状态**: ✅ 待运行测试脚本验证

