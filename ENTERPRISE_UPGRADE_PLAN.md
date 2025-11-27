# Sport Agent V3 → 企业级平台升级计划

基于资深产品总监的评审反馈，制定以下系统性升级路线。

---

## 评审总结

### 当前状态
✅ **已具备的优势**：
- 清晰的目录分层结构
- 零硬编码实体映射
- 多 LLM 支持
- 异步 FastAPI + PostgreSQL
- 完整的文档体系

❌ **关键问题**：
1. **最紧急**：Agent 编造数据（已修复）
2. **架构层**：LangChain 边界不够清晰
3. **产品层**：意图分类还不够"产品化"
4. **数据层**：缺少 Source 抽象和模型生命周期
5. **工程层**：缺少 CI/CD 和测试规范

---

## 升级路线图

### 阶段0：紧急修复（已完成）

**问题**：Agent 在没有数据时编造虚假信息

**修复**：
- ✅ 重写 Supervisor Prompt，严格禁止编造数据
- ✅ 要求所有数据必须来自工具返回
- ✅ 数据缺失时诚实告知用户

**验证**：
```bash
python scripts/chat_interactive.py
# 测试："比萨最近战绩"
# 预期：明确告知"数据库中没有数据"，而不是编造
```

---

### 阶段1：架构边界强化（1周）

#### 1.1 创建 LangChain Adapter 层

**目标**：隔离 LangChain 依赖，防止污染全局

**任务**：
```
src/agent/langchain_adapters/
├── __init__.py
├── agent_adapter.py       # 将领域 Agent 适配为 LangChain Agent
├── tool_adapter.py        # 将领域 Tool 适配为 LangChain Tool
└── result_adapter.py      # 将 LangChain 输出转为领域对象
```

**核心接口**：
```python
# src/agent/domain/agent_interface.py
from abc import ABC, abstractmethod

class AgentResult:
    """领域层的统一返回"""
    answer: str
    confidence: float
    data_sources: List[str]
    tools_used: List[str]

class DomainAgent(ABC):
    """领域 Agent 接口（不依赖 LangChain）"""
    
    @abstractmethod
    async def handle_query(self, query: str, context: dict) -> AgentResult:
        pass
```

**架构红线（写入文档）**：
- 禁止在 `src/services/`, `src/infra/`, `src/ml/` 中导入 langchain
- 所有 LangChain 代码必须在 `src/agent/langchain_adapters/` 下
- Service 层只认领域接口，不认 LangChain API

---

#### 1.2 实现监督智能体（Supervisor Agent）

**目标**：显式的多智能体架构

**架构图**：
```
SupervisorAgent（监督者）
├── 场景识别
├── 专家选择
├── 安全策略检查
└── 结果合成
    ↓
┌──────────────┬──────────────┬──────────────┐
│ StatsAgent   │ PredictAgent │ ExplainAgent │
│ (纯数据)     │ (ML模型)     │ (LLM解释)    │
└──────────────┴──────────────┴──────────────┘
```

**文件结构**：
```
src/supervisor/
├── __init__.py
├── supervisor_agent.py      # 监督者核心
├── scene_router.py          # 场景路由器
├── expert_selector.py       # 专家选择器
└── safety_checker.py        # 安全策略检查
```

**关键代码**：
```python
class SupervisorAgent:
    """监督智能体"""
    
    def __init__(self):
        self._scene_router = SceneRouter()
        self._expert_selector = ExpertSelector()
        self._safety_checker = SafetyChecker()
        
        # 注册专家
        self._experts = {
            "stats": StatsAgent(),
            "predict": PredictAgent(),
            "explain": ExplainAgent()
        }
    
    async def handle_query(self, query: str, context: dict) -> AgentResult:
        # 1. 识别场景
        scene = await self._scene_router.identify(query)
        
        # 2. 安全检查
        if not self._safety_checker.is_allowed(scene):
            return AgentResult(
                answer="抱歉，该类型的问题超出服务范围",
                confidence=1.0
            )
        
        # 3. 选择专家
        experts = self._expert_selector.select(scene)
        
        # 4. 执行专家
        results = await self._execute_experts(experts, query, context)
        
        # 5. 合成答案
        return self._synthesize_results(results)
```

---

### 阶段2：业务产品化（2周）

#### 2.1 场景化 Skill Pack

**目标**：从"意图分类"升级到"场景包"

**文件结构**：
```
config/skill_packs/
├── betting_decision.yaml     # 投注决策场景
├── media_analysis.yaml       # 媒体分析场景
├── club_scouting.yaml        # 球探侦查场景
└── default.yaml              # 默认场景
```

**场景定义示例**：
```yaml
# betting_decision.yaml
name: "投注决策助手"
description: "为投注决策提供数据支持"

enabled_scenes:
  - match_prediction
  - team_comparison
  - injury_analysis

disabled_scenes:
  - direct_betting_advice  # 禁止直接给投注建议

output_schema:
  type: "structured"
  format: "json"
  required_fields:
    - home_win_prob
    - draw_prob
    - away_win_prob
    - confidence_score
    - key_factors

safety_rules:
  - no_gambling_promotion
  - require_disclaimer
  - probability_only

sla:
  response_time_p95: 3000  # ms
  accuracy_target: 0.65
```

**加载逻辑**：
```python
class SkillPackManager:
    """Skill Pack 管理器"""
    
    def load_pack(self, pack_name: str) -> SkillPack:
        """根据租户/用户加载对应的 Skill Pack"""
        config = load_yaml(f"config/skill_packs/{pack_name}.yaml")
        return SkillPack(config)
    
    def is_scene_allowed(self, pack: SkillPack, scene: str) -> bool:
        """检查场景是否允许"""
        return scene in pack.enabled_scenes
```

---

#### 2.2 标准化输出结构

**目标**：结构化输出，而不仅仅是自然语言

**定义输出 Schema**：
```python
# src/agent/domain/output_schemas.py

class PredictionOutput(BaseModel):
    """预测输出标准结构"""
    
    # 核心预测
    home_win_prob: float = Field(..., ge=0, le=1)
    draw_prob: float = Field(..., ge=0, le=1)
    away_win_prob: float = Field(..., ge=0, le=1)
    
    # 置信度
    confidence_score: float = Field(..., ge=0, le=1)
    data_quality_score: float = Field(..., ge=0, le=1)
    
    # 关键因素（可解释性）
    key_factors: List[KeyFactor]
    
    # 元数据
    model_version: str
    prediction_time: datetime
    data_sources: List[str]
    
    # 自然语言解释（可选）
    natural_explanation: Optional[str] = None


class KeyFactor(BaseModel):
    """关键影响因素"""
    factor_type: str  # "form", "injury", "h2h", "venue"
    importance: float  # 0-1
    direction: str     # "favor_home", "favor_away", "neutral"
    detail: str        # 人类可读的说明
```

**使用示例**：
```python
# Agent 返回结构化数据
prediction = await predict_agent.predict("曼联 vs 利物浦")

# 前端直接使用
display_probability_chart(
    home=prediction.home_win_prob,
    draw=prediction.draw_prob,
    away=prediction.away_win_prob
)

# BI 系统直接分析
df = pd.DataFrame([p.dict() for p in predictions])

# LLM 负责生成自然语言（可选）
if user_wants_explanation:
    explanation = llm.explain(prediction)
```

---

#### 2.3 失败降级策略

**目标**：企业级的 5% 失败处理

**降级策略定义**：
```python
# src/agent/domain/fallback_strategy.py

class FallbackStrategy:
    """失败降级策略"""
    
    @staticmethod
    async def handle_data_insufficient(query: str) -> AgentResult:
        """数据不足时的降级"""
        # 尝试查找历史相似比赛
        similar_matches = await find_similar_historical_matches(query)
        
        if similar_matches:
            return AgentResult(
                answer=f"数据库中没有该比赛的直接数据，但找到{len(similar_matches)}场相似比赛供参考...",
                confidence=0.3,
                fallback_mode="historical_reference"
            )
        else:
            return AgentResult(
                answer="抱歉，数据库中没有相关数据，暂时无法提供分析",
                confidence=0.0,
                fallback_mode="no_data"
            )
    
    @staticmethod
    async def handle_model_failure(query: str) -> AgentResult:
        """模型异常时的降级"""
        # 降级为纯统计分析
        stats = await calculate_basic_stats(query)
        
        return AgentResult(
            answer=f"预测模型暂时不可用，基于统计数据：{stats}",
            confidence=0.4,
            fallback_mode="stats_only"
        )
    
    @staticmethod
    async def handle_llm_timeout(query: str) -> AgentResult:
        """LLM 超时时的降级"""
        # 返回结构化模板
        template = load_template("llm_timeout")
        
        return AgentResult(
            answer=template.render(query=query),
            confidence=0.5,
            fallback_mode="template"
        )
```

---

### 阶段3：数据产品化（2周）

#### 3.1 Data Source 抽象

**目标**：解耦数据源，支持多种来源

**接口定义**：
```python
# src/data_pipeline/providers/base.py

from abc import ABC, abstractmethod

class MatchDataProvider(ABC):
    """比赛数据提供者接口"""
    
    @abstractmethod
    async def get_matches(
        self, 
        league: str, 
        date_range: tuple
    ) -> List[Match]:
        """获取比赛数据"""
        pass
    
    @abstractmethod
    async def get_teams(self, league: str) -> List[Team]:
        """获取球队数据"""
        pass
    
    @abstractmethod
    async def get_standings(self, league: str) -> List[Standing]:
        """获取积分榜"""
        pass
```

**实现示例**：
```
src/data_pipeline/providers/
├── __init__.py
├── base.py                      # 基础接口
├── football_data_org.py         # football-data.org 实现
├── internal_db.py               # 内部数据库实现
├── opta.py                      # Opta Sports 实现（示例）
└── csv_file.py                  # CSV 文件实现（测试用）
```

**配置化选择**：
```yaml
# config/data_sources.yaml
primary_source:
  provider: "football_data_org"
  api_key: "${FOOTBALL_DATA_API_KEY}"
  
fallback_sources:
  - provider: "internal_db"
    connection: "${DATABASE_URL}"

tenant_overrides:
  tenant_a:
    provider: "opta"
    api_key: "${OPTA_API_KEY}"
```

---

#### 3.2 模型生命周期管理

**目标**：企业级的模型版本控制

**Model Registry 设计**：
```python
# src/ml/model_registry/registry.py

class ModelRegistry:
    """模型注册表"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.metadata_db = self._init_db()
    
    def register_model(
        self,
        name: str,
        version: str,
        model_path: str,
        metrics: Dict[str, float],
        training_data_range: tuple
    ) -> ModelInfo:
        """注册新模型版本"""
        
        model_info = ModelInfo(
            name=name,
            version=version,
            model_path=model_path,
            metrics=metrics,
            training_data_range=training_data_range,
            registered_at=datetime.now(),
            status="registered"
        )
        
        self.metadata_db.save(model_info)
        return model_info
    
    def promote_to_production(self, name: str, version: str):
        """提升模型到生产环境"""
        model = self.metadata_db.get(name, version)
        
        # 降级当前生产模型
        current_prod = self.get_production_model(name)
        if current_prod:
            current_prod.status = "retired"
            self.metadata_db.update(current_prod)
        
        # 提升新模型
        model.status = "production"
        model.promoted_at = datetime.now()
        self.metadata_db.update(model)
    
    def get_production_model(self, name: str) -> ModelInfo:
        """获取当前生产模型"""
        return self.metadata_db.query(
            name=name, 
            status="production"
        ).first()
```

**Metadata Schema**：
```python
class ModelInfo(BaseModel):
    """模型元数据"""
    name: str
    version: str
    model_path: str
    
    # 训练信息
    training_data_range: tuple[date, date]
    training_samples: int
    training_duration_seconds: float
    
    # 性能指标
    metrics: Dict[str, float]  # accuracy, precision, recall, f1, auc
    
    # 生命周期
    registered_at: datetime
    promoted_at: Optional[datetime]
    retired_at: Optional[datetime]
    status: str  # registered, production, retired
    
    # 可追溯性
    git_commit: Optional[str]
    docker_image: Optional[str]
    created_by: Optional[str]
```

---

#### 3.3 特征工程文档化

**目标**：可解释、可审计的特征设计

**创建文档**：`docs/ML_FEATURE_DESIGN.md`

**内容包括**：
1. **特征定义表**：
   ```markdown
   | 特征名 | 类型 | 时间窗 | 计算逻辑 | 数据泄露风险 |
   |-------|------|--------|---------|--------------|
   | team_form_last_5 | float | 过去5场 | 胜3分平1分负0分的平均 | ✅ 无 |
   | opponent_strength | float | 当前赛季 | 基于积分排名归一化 | ✅ 无 |
   | player_availability | float | 比赛日 | 主力可用比例 | ⚠️ 需确认数据获取时间 |
   ```

2. **时间窗说明**：
   - 所有特征基于"比赛开始前24小时可获得的数据"
   - 禁止使用未来信息（如比赛结果、比赛后的评分）

3. **数据泄露检查清单**：
   - [ ] 特征计算时间点 < 比赛开始时间
   - [ ] 不包含比赛结果相关字段
   - [ ] 外部数据的发布时间 < 比赛开始时间

---

### 阶段4：工程化强化（1周）

#### 4.1 极简 CI/CD

**创建 `.github/workflows/ci.yml`**：
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest ruff black
    
    - name: Lint with ruff
      run: ruff check src/
    
    - name: Format check
      run: black --check src/
    
    - name: Run tests
      run: pytest tests/ -v
      
    - name: Agent evaluation
      run: python scripts/run_agent_eval.py
```

#### 4.2 Agent 回归测试

**创建测试数据集**：`tests/agent_eval/golden_queries.yaml`

```yaml
queries:
  - id: "q001"
    query: "曼联最近5场比赛战绩如何？"
    expected_intent: "recent_matches"
    expected_tools: ["data_stats_expert"]
    validation:
      must_call_tool: true
      must_not_fabricate_data: true
      min_answer_length: 50
  
  - id: "q002"
    query: "比萨最近战绩"
    expected_intent: "recent_matches"
    validation:
      if_no_data_must_say: "没有数据"
      must_not_fabricate: true
  
  - id: "q003"
    query: "预测曼联对利物浦"
    expected_intent: "match_prediction"
    expected_tools: ["prediction_expert"]
    validation:
      must_return_probabilities: true
      probability_sum_equals_one: true
```

**评测脚本**：`scripts/run_agent_eval.py`

```python
async def run_evaluation():
    """运行 Agent 评估"""
    queries = load_yaml("tests/agent_eval/golden_queries.yaml")
    
    results = []
    for q in queries["queries"]:
        result = await agent.handle_query(q["query"])
        
        # 验证
        passed = validate_result(result, q["validation"])
        
        results.append({
            "query_id": q["id"],
            "passed": passed,
            "response_time": result.duration,
            "tools_used": result.tools_used
        })
    
    # 生成报告
    report = generate_report(results)
    print(report)
    
    # CI 中失败条件
    if report["pass_rate"] < 0.95:
        sys.exit(1)
```

---

#### 4.3 日志和追踪规范

**统一日志格式**：
```python
# src/shared/logging_config.py

import structlog

def setup_logging():
    """配置结构化日志"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

**使用示例**：
```python
logger = structlog.get_logger()

# 记录 LLM 调用
logger.info(
    "llm_call",
    request_id=request_id,
    provider="ollama",
    model="qwen2.5:7b",
    prompt_tokens=150,
    completion_tokens=300,
    duration_ms=8500,
    success=True
)

# 记录 Agent 调用
logger.info(
    "agent_query",
    request_id=request_id,
    query=query[:100],
    intent="match_prediction",
    tools_used=["data_stats_expert", "prediction_expert"],
    confidence=0.85,
    duration_ms=12000
)
```

---

### 阶段5：差异化能力（2-3周）

#### 5.1 解释型预测引擎

**目标**：XGBoost + SHAP + LLM 组合拳

**实现流程**：
```python
class ExplainablePredictionEngine:
    """可解释预测引擎"""
    
    async def predict_with_explanation(
        self, 
        home_team: str, 
        away_team: str
    ) -> ExplainablePrediction:
        
        # 1. 获取特征
        features = await self._build_features(home_team, away_team)
        
        # 2. 模型预测
        prediction = self.model.predict_proba(features)
        
        # 3. SHAP 解释
        shap_values = self.explainer.shap_values(features)
        
        # 4. 映射为领域语义
        factor_explanations = self._map_to_domain(shap_values, features)
        
        # 5. LLM 生成自然语言（可选）
        natural_explanation = await self._generate_explanation(
            prediction, 
            factor_explanations
        )
        
        return ExplainablePrediction(
            home_win_prob=prediction[0],
            draw_prob=prediction[1],
            away_win_prob=prediction[2],
            key_factors=factor_explanations,
            natural_explanation=natural_explanation
        )
    
    def _map_to_domain(self, shap_values, features) -> List[KeyFactor]:
        """将 SHAP 值映射为领域因素"""
        factors = []
        
        for feat_name, shap_val in zip(features.columns, shap_values[0]):
            importance = abs(shap_val)
            direction = "favor_home" if shap_val > 0 else "favor_away"
            
            detail = self._generate_factor_detail(feat_name, features[feat_name], shap_val)
            
            factors.append(KeyFactor(
                factor_type=self._get_factor_type(feat_name),
                importance=importance,
                direction=direction,
                detail=detail
            ))
        
        # 按重要性排序，返回 Top 5
        return sorted(factors, key=lambda x: x.importance, reverse=True)[:5]
```

**输出示例**：
```json
{
  "home_win_prob": 0.42,
  "draw_prob": 0.28,
  "away_win_prob": 0.30,
  "key_factors": [
    {
      "factor_type": "form",
      "importance": 0.35,
      "direction": "favor_home",
      "detail": "主队曼联近5场3胜，客队利物浦近5场2胜"
    },
    {
      "factor_type": "h2h",
      "importance": 0.25,
      "direction": "favor_away",
      "detail": "历史交锋利物浦占优，最近3次2胜1平"
    }
  ],
  "natural_explanation": "根据模型分析，曼联主场获胜概率为42%。主要影响因素：1）曼联近期状态更好（贡献35%）；2）但历史交锋利物浦占优（-25%）..."
}
```

---

#### 5.2 内核-外设架构拆分

**目标**：提前为多渠道部署准备

**目录重构**：
```
sport_agent/
├── sport_agent_core/          # 核心内核（纯 Python）
│   ├── agent/
│   ├── services/
│   ├── ml/
│   └── infra/
│
├── sport_agent_api/           # HTTP 接口
│   ├── main.py
│   ├── routers/
│   └── dependencies.py
│
├── sport_agent_cli/           # 命令行接口
│   └── cli.py
│
└── sport_agent_worker/        # 后台任务
    ├── train_models.py
    └── sync_data.py
```

**Core 层接口**：
```python
# sport_agent_core/interface.py

class SportAgentCore:
    """核心接口（不依赖 HTTP）"""
    
    async def query(
        self, 
        query: str, 
        context: QueryContext
    ) -> AgentResult:
        """处理用户查询"""
        pass
    
    async def predict(
        self, 
        home_team: str, 
        away_team: str
    ) -> PredictionOutput:
        """预测比赛结果"""
        pass
    
    async def get_team_stats(
        self, 
        team_name: str
    ) -> TeamStats:
        """获取球队统计"""
        pass
```

**API 层调用**：
```python
# sport_agent_api/main.py

from sport_agent_core import SportAgentCore

core = SportAgentCore()

@app.post("/v1/query")
async def query_endpoint(request: QueryRequest):
    """HTTP 端点（只做转换）"""
    context = QueryContext(
        user_id=request.user_id,
        session_id=request.session_id,
        tenant_id=request.tenant_id
    )
    
    result = await core.query(request.query, context)
    
    return QueryResponse.from_agent_result(result)
```

---

## 总结

### 立即行动（本周）
1. ✅ 修复 Agent 编造数据问题（已完成）
2. 添加基本 CI（linting + 格式检查）
3. 创建 Agent 回归测试数据集
4. 编写日志规范文档

### 短期目标（2-4周）
1. 实现 LangChain Adapter 隔离
2. 重构为显式的 Supervisor + Expert 架构
3. 设计 Skill Pack 配置系统
4. 添加标准化输出结构

### 中期目标（1-2月）
1. 实现 Data Source 抽象
2. 建立 Model Registry
3. 开发解释型预测引擎
4. 拆分 Core / API 架构

### 长期愿景（3-6月）
1. 多租户 Skill Pack 系统
2. 完整的模型生命周期管理
3. 企业级监控和告警
4. Web UI + 多渠道部署

---

**参考文档**：
- 基于资深产品总监评审反馈
- 当前代码库：sport-agent-mvp
- 架构文档：ARCHITECTURE_CURRENT.md

