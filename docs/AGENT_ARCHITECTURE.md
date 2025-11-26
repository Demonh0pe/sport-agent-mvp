# Sport Event Agent 架构设计

**版本**: v3.0
**日期**: 2025-11-26
**基于**: sport event agent.pdf 企业级设计文档

---

## 一、架构总览

### 1.1 设计理念

本架构遵循PDF文档的核心原则：
1. ✅ **业务逻辑优先** - 场景驱动设计，而非技术驱动
2. ✅ **模块化与可扩展** - 核心功能稳定，扩展功能插件化
3. ✅ **容错与降级** - 每个环节都有降级策略
4. ✅ **可解释性优先** - 不仅给出结果，还要解释原因

### 1.2 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层 (User Interface)              │
│              - Web/Mobile UI   - Chat Interface          │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                  对话引擎层 (Dialog Engine)                 │
│   - 意图识别   - 实体提取   - 上下文管理   - 对话降级        │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                  业务编排层 (Business Orchestrator)        │
│          - 场景路由   - 业务流程   - 策略选择              │
└─────────────────────────────────────────────────────────┘
                              ↓
┌───────────────┬─────────────┬─────────────┬──────────────┐
│  预测服务      │  推荐服务    │  分析服务    │   资讯服务     │
│ (Prediction)  │(Recommend)  │ (Analysis)  │    (News)     │
└───────────────┴─────────────┴─────────────┴──────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                   数据服务层 (Data Services)               │
│      - 数据查询   - 特征计算   - 缓存管理   - 质量检测      │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                    基础设施层 (Infrastructure)             │
│         - PostgreSQL   - Redis   - MQ   - Monitoring     │
└─────────────────────────────────────────────────────────┘
```

---

## 二、核心模块设计（MVP - 2周内完成）

### 2.1 对话引擎 (Dialog Engine)

**职责**: 理解用户输入，管理对话上下文

#### 子模块

##### 2.1.1 意图分类器 (Intent Classifier)

**文件**: `src/agent/dialog/intent_classifier.py`

```python
class IntentClassifier:
    """
    意图分类体系（对应PDF 4.1）

    支持的意图类型：
    - query: 查询类（战绩、排名、数据）
    - prediction: 预测类（谁会赢、比分预测）
    - recommendation: 推荐类（今晚看什么、值得看的比赛）
    - analysis: 分析类（为什么、怎么样、状态分析）
    - comparison: 对比类（两队对比、历史交锋）
    - news: 资讯类（新闻、伤病、转会）
    - clarification: 澄清类（意图不明确时的反问）

    边界场景：
    - 意图不明确 → 反问澄清
    - 多意图混合 → 拆分为多个子任务
    - 超出能力范围 → 诚实告知
    """

    async def classify(self, user_input: str, context: ConversationContext) -> Intent
    async def resolve_ambiguity(self, user_input: str) -> ClarificationQuestion
```

**实现方式**:
- 阶段1（MVP）: 基于规则 + 关键词 + LLM分类
- 阶段2（优化）: 集成transformers零样本分类模型
- 阶段3（生产）: 微调的BERT分类器

**扩展点**:
```python
# 扩展接口：自定义意图
class CustomIntentHandler(Protocol):
    async def handle(self, input: str) -> Intent

# 注册自定义意图
intent_classifier.register_custom_intent("betting_advice", BettingIntentHandler())
```

##### 2.1.2 实体识别器 (Entity Recognizer)

**文件**: `src/agent/dialog/entity_recognizer.py`

```python
class EntityRecognizer:
    """
    实体识别与标准化（对应PDF 4.2）

    核心实体：
    - Team: 球队（支持别称：曼联/Manchester United/MUN）
    - League: 联赛（英超/EPL/Premier League）
    - Match: 比赛（曼联vs利物浦）
    - Player: 球员（C罗/Ronaldo）
    - Time: 时间表达（今晚/本周末/明天）

    标准化规则：
    - 多种表达映射到标准实体
    - 模糊匹配容忍拼写错误
    - 歧义消解（当"曼联"可能指多个实体）
    """

    async def extract_entities(self, text: str) -> List[Entity]
    async def normalize(self, entity: Entity) -> StandardEntity
    async def resolve_ambiguity(self, candidates: List[Entity]) -> Entity
```

**扩展点**:
```python
# 扩展接口：新实体类型
class EntityMapper(Protocol):
    def map(self, text: str) -> Optional[Entity]

# 注册新实体映射器
entity_recognizer.register_mapper("stadium", StadiumMapper())
```

##### 2.1.3 上下文管理器 (Context Manager)

**文件**: `src/agent/dialog/context_manager.py`

```python
class ContextManager:
    """
    上下文管理策略（对应PDF 4.3）

    上下文状态：
    - current_topic: 当前话题（比赛、球队、联赛）
    - history_messages: 历史消息（最近5轮）
    - user_profile: 用户画像（偏好球队、联赛）
    - session_data: 会话数据（临时变量）

    引用规则：
    - 代词消解："他们" → 上文提到的球队
    - 省略补全："最近状态？" → "曼联最近状态"
    - 话题切换检测：识别话题转换，清空不相关上下文

    过期策略：
    - 时间TTL: 5分钟无交互清空
    - 话题切换: 明确换话题时清空
    - 用户主动重置: "重新开始"
    """

    async def update(self, message: Message, response: Response)
    async def get_context(self, session_id: str) -> ConversationContext
    async def resolve_reference(self, text: str, context: ConversationContext) -> str
    async def detect_topic_switch(self, new_message: str, context: ConversationContext) -> bool
```

**扩展点**:
```python
# 扩展接口：自定义上下文存储
class ContextStore(Protocol):
    async def save(self, session_id: str, context: ConversationContext)
    async def load(self, session_id: str) -> ConversationContext

# 支持Redis、PostgreSQL、内存等多种存储
context_manager.set_store(RedisContextStore())
```

##### 2.1.4 对话降级策略 (Fallback Strategy)

**文件**: `src/agent/dialog/fallback.py`

```python
class FallbackStrategy:
    """
    对话降级策略（对应PDF 4.4）

    降级场景：
    1. 无法识别意图 → 提供引导菜单或反问澄清
    2. 实体无法识别 → 主动澄清或模糊匹配
    3. 查询无结果 → 告知无结果并推荐相关内容
    4. 服务失败 → 降级到规则推断或诚实告知
    """

    async def handle_unknown_intent(self, input: str) -> Response
    async def handle_entity_not_found(self, entity: str) -> Response
    async def handle_no_results(self, query: Query) -> Response
    async def handle_service_failure(self, error: Exception) -> Response
```

---

### 2.2 业务编排器 (Business Orchestrator)

**职责**: 根据意图选择业务场景，编排服务调用

**文件**: `src/agent/orchestrator/business_orchestrator.py`

```python
class BusinessOrchestrator:
    """
    业务场景编排（对应PDF文档9大场景）

    场景路由：
    - Intent.PREDICTION → PredictionScenario
    - Intent.RECOMMENDATION → RecommendationScenario
    - Intent.ANALYSIS → AnalysisScenario
    - Intent.COMPARISON → ComparisonScenario
    - Intent.QUERY → QueryScenario
    - Intent.NEWS → NewsScenario
    """

    async def route(self, intent: Intent, entities: List[Entity], context: Context) -> Scenario
    async def orchestrate(self, scenario: Scenario) -> Response
```

#### 场景实现

##### 场景1: 预测场景 (Prediction Scenario)

**文件**: `src/agent/scenarios/prediction_scenario.py`

```python
class PredictionScenario:
    """
    预测场景："曼联对利物浦谁会赢？"

    业务流程（对应PDF 1.2）：
    1. 实体识别：提取主队、客队、联赛
    2. 歧义处理：如果不明确，澄清（"您说的是英超还是欧冠？"）
    3. 预测调用：调用预测服务
    4. 结果解释：不仅给概率，还要解释为什么
    5. 风险提示：指出可能改变结果的因素

    降级策略：
    - 预测服务不可用 → 基于规则推断 + 诚实告知
    - 数据不足 → 告知数据缺失，给出保守建议
    """

    async def execute(self, entities: Dict, context: Context) -> PredictionResponse
```

##### 场景2: 推荐场景 (Recommendation Scenario)

**文件**: `src/agent/scenarios/recommendation_scenario.py`

```python
class RecommendationScenario:
    """
    推荐场景："今晚看什么比赛？"

    业务流程（对应PDF 5.1-5.3）：
    1. 召回策略：
       - 基于用户偏好（历史关注的球队）
       - 基于比赛热度（重要比赛、德比）
       - 基于预测特征（实力接近、精彩度高）
       - 基于时间（今晚/本周末）

    2. 排序因子：
       - 兴趣匹配度 (40%)
       - 比赛精彩度 (30%)
       - 比赛重要性 (20%)
       - 时间便利性 (10%)

    3. 多样性控制：避免推荐单一联赛

    4. 冷启动：
       - 新用户：推荐热门比赛 + 快速问卷
       - 新比赛：基于联赛重要性和球队排名
    """

    async def execute(self, entities: Dict, context: Context) -> RecommendationResponse
```

##### 场景3: 分析场景 (Analysis Scenario)

**文件**: `src/agent/scenarios/analysis_scenario.py`

```python
class AnalysisScenario:
    """
    分析场景："为什么利物浦排名第一？" "曼联最近怎么了？"

    业务流程：
    1. 数据收集：排名、战绩、进失球、近期走势
    2. 多维度分析：
       - 数据层面：战绩、进攻、防守
       - 赛程层面：对手强度、赛程密度
       - 人员层面：伤病、状态
    3. 根本原因识别：找出最核心的1-2个问题
    4. 趋势预测：是上升还是下降
    """

    async def execute(self, entities: Dict, context: Context) -> AnalysisResponse
```

##### 场景4-9: 其他场景（预留接口）

```python
# 场景4: 对比场景
class ComparisonScenario: pass

# 场景5: 查询场景
class QueryScenario: pass

# 场景6: 资讯场景
class NewsScenario: pass

# 场景7: 数据探索场景（重度用户）
class DataExplorationScenario: pass

# 场景8: 趋势场景
class TrendScenario: pass

# 场景9: 澄清场景
class ClarificationScenario: pass
```

**扩展接口**:
```python
class ScenarioPlugin(Protocol):
    """场景插件接口"""
    def can_handle(self, intent: Intent) -> bool
    async def execute(self, entities: Dict, context: Context) -> Response

# 注册新场景
orchestrator.register_scenario("betting_advice", BettingAdviceScenario())
```

---

### 2.3 预测服务 (Prediction Service)

**职责**: 提供比赛预测能力

**文件**: `src/agent/services/prediction_service.py`

```python
class PredictionService:
    """
    预测服务（对应PDF 第3节）

    预测目标（对应PDF 1.1）：
    - 胜平负预测 (Home/Draw/Away)
    - 概率分布 (probabilities)
    - 置信区间 (confidence_interval)

    预测时机：
    - 赛前24小时（T-24h）
    - 赛前1小时（T-1h）
    - 实时更新（Live）- 未来扩展

    可解释性（对应PDF 3.2）：
    - 特征贡献 → 自然语言映射
    - 解释层次：简明结论 → 关键因素 → 详细数据
    - 不确定性表达：诚实告知概率

    模型失效检测（对应PDF 3.3）：
    - 失效信号：准确率持续下降、异常案例激增
    - 触发阈值：准确率 < 50% 持续3天
    - 响应策略：降级到规则预测 + 报警
    """

    async def predict(
        self,
        home_team: str,
        away_team: str,
        league: str,
        phase: str = "T-24h"
    ) -> PredictionResult

    async def explain(self, prediction: PredictionResult) -> Explanation

    async def check_model_health(self) -> HealthStatus
```

**PredictionResult数据结构**:
```python
@dataclass
class PredictionResult:
    """预测结果"""
    prediction: str  # "H" / "D" / "A"
    probabilities: Dict[str, float]  # {"H": 0.4, "D": 0.3, "A": 0.3}
    confidence: float  # 0-1

    # 可解释性
    key_factors: List[Factor]  # 关键因素（从ReasoningEngine获取）
    causal_chain: List[str]  # 因果链
    risk_factors: List[str]  # 风险因素

    # 元数据
    model_version: str
    prediction_time: datetime
    data_quality_score: float
```

**扩展点**:
```python
# 扩展接口：比分预测、让球盘预测
class ScorePredictorPlugin(Protocol):
    async def predict_score(self, match: Match) -> ScorePrediction

prediction_service.register_plugin("score", XGBoostScorePredictor())
```

---

### 2.4 推荐服务 (Recommendation Service)

**职责**: 提供比赛推荐能力

**文件**: `src/agent/services/recommendation_service.py`

```python
class RecommendationService:
    """
    推荐服务（对应PDF 第5节）

    推荐目标（对应PDF 5.1）：
    - 优化目标：最大化用户满意度
    - 约束条件：时效性、数据可靠性
    - 评估指标：点击率、观看率、多样性

    召回策略（对应PDF 5.2）：
    - 基于用户偏好（协同过滤）
    - 基于比赛热度（热门赛事）
    - 基于预测特征（实力接近、精彩度）
    - 基于时间（即将开始）

    排序因子：
    - 兴趣匹配: 40%
    - 比赛精彩度: 30%
    - 比赛重要性: 20%
    - 时间便利性: 10%

    冷启动策略（对应PDF 5.3）：
    - 新用户：默认推荐热门比赛
    - 新比赛：基于联赛和球队历史
    """

    async def recommend(
        self,
        user_id: str,
        filters: Dict,
        top_k: int = 5
    ) -> List[MatchRecommendation]

    async def explain_recommendation(
        self,
        match: Match,
        user_id: str
    ) -> str
```

**扩展点**:
```python
# 扩展接口：自定义召回策略
class RecallStrategy(Protocol):
    async def recall(self, user_id: str, filters: Dict) -> List[Match]

# 扩展接口：自定义排序策略
class RankingStrategy(Protocol):
    def score(self, match: Match, user: User) -> float

recommendation_service.add_recall_strategy("social", SocialRecallStrategy())
recommendation_service.set_ranking_strategy(MLRankingStrategy())
```

---

### 2.5 分析服务 (Analysis Service)

**职责**: 提供深度数据分析能力

**文件**: `src/agent/services/analysis_service.py`

```python
class AnalysisService:
    """
    分析服务

    分析类型：
    1. 球队状态分析：近期走势、优劣势、问题诊断
    2. 对比分析：两队全方位对比
    3. 趋势分析：排名走势、状态曲线
    4. 根本原因分析：为什么排名高/低
    """

    async def analyze_team_status(self, team: str) -> TeamAnalysis
    async def compare_teams(self, team_a: str, team_b: str) -> ComparisonResult
    async def analyze_trend(self, team: str, window: int) -> TrendAnalysis
    async def explain_ranking(self, team: str) -> RankingExplanation
```

**集成已创建的组件**:
- 使用 `DataAnalyzer` 提取和对比数据
- 使用 `ReasoningEngine` 进行深度推理
- 生成可解释的分析报告

---

### 2.6 数据服务 (Data Service)

**职责**: 统一的数据访问层

**文件**: `src/agent/services/data_service.py`

```python
class DataService:
    """
    数据服务（对应PDF 第2节）

    数据质量管理（对应PDF 2.3）：
    - 完整性检查：必填字段验证
    - 一致性校验：比分与结果逻辑校验
    - 异常值检测：统计阈值检测
    - 更新时效性：赛后更新SLA

    特征计算（对应PDF 2.2）：
    - 基础特征：近N场胜率、主客场表现
    - 衍生特征：近期势头、赛程疲劳度
    - 避免数据泄露：严格时间切分
    """

    async def get_match(self, match_id: str) -> Match
    async def get_team_stats(self, team: str, window: int) -> TeamStats
    async def get_h2h(self, team_a: str, team_b: str, limit: int) -> List[Match]
    async def compute_features(self, match: Match) -> Features
    async def check_data_quality(self, data: Any) -> QualityReport
```

---

## 三、系统集成（AgentServiceV3）

**文件**: `src/agent/agent_service_v3.py`

```python
class AgentServiceV3:
    """
    Agent服务v3.0 - 完整的企业级Agent

    集成所有模块：
    1. DialogEngine - 对话理解
    2. BusinessOrchestrator - 业务编排
    3. PredictionService - 预测能力
    4. RecommendationService - 推荐能力
    5. AnalysisService - 分析能力
    6. DataService - 数据访问

    容错与降级（对应PDF 6.3）：
    - 每个服务都有降级策略
    - 超时与重试：2秒超时，最多重试2次
    - 熔断机制：连续5次失败后熔断30秒
    """

    def __init__(self):
        # 对话引擎
        self.intent_classifier = IntentClassifier()
        self.entity_recognizer = EntityRecognizer()
        self.context_manager = ContextManager()
        self.fallback = FallbackStrategy()

        # 业务编排
        self.orchestrator = BusinessOrchestrator()

        # 业务服务
        self.prediction_service = PredictionService()
        self.recommendation_service = RecommendationService()
        self.analysis_service = AnalysisService()
        self.data_service = DataService()

        # 核心组件（已创建）
        self.reasoning_engine = ReasoningEngine()
        self.data_analyzer = DataAnalyzer()

    async def chat(self, user_input: str, session_id: str) -> AgentResponse:
        """
        主聊天接口

        流程：
        1. 对话理解 (Dialog Engine)
        2. 业务路由 (Orchestrator)
        3. 场景执行 (Scenario)
        4. 答案生成 (Answer Generator)
        5. 上下文更新 (Context Manager)
        """
        try:
            # 1. 获取上下文
            context = await self.context_manager.get_context(session_id)

            # 2. 代词消解
            resolved_input = await self.context_manager.resolve_reference(
                user_input,
                context
            )

            # 3. 意图识别
            intent = await self.intent_classifier.classify(resolved_input, context)

            # 4. 实体提取
            entities = await self.entity_recognizer.extract_entities(resolved_input)

            # 5. 业务路由
            scenario = await self.orchestrator.route(intent, entities, context)

            # 6. 场景执行
            response = await scenario.execute(entities, context)

            # 7. 上下文更新
            await self.context_manager.update(user_input, response)

            return response

        except IntentNotClearException:
            # 降级：反问澄清
            return await self.fallback.handle_unknown_intent(user_input)

        except ServiceUnavailableException as e:
            # 降级：诚实告知
            return await self.fallback.handle_service_failure(e)
```

---

## 四、扩展点设计

### 4.1 插件化架构

所有扩展功能都通过插件接口注册：

```python
# 1. 自定义意图
agent.register_intent("betting", BettingIntentHandler())

# 2. 自定义场景
agent.register_scenario("live_commentary", LiveCommentaryScenario())

# 3. 自定义预测模型
agent.register_predictor("neural_net", NeuralNetPredictor())

# 4. 自定义推荐策略
agent.register_recall_strategy("trending", TrendingRecallStrategy())

# 5. 自定义实体
agent.register_entity_mapper("stadium", StadiumMapper())
```

### 4.2 预留扩展功能

以下功能设计了接口，但暂不实现（后期扩展）：

#### ✅ **已预留 - 赛中实时预测**
```python
class LivePredictionService:
    """赛中实时预测（未来扩展）"""
    async def predict_live(self, match_id: str, live_data: LiveData) -> LivePrediction
```

#### ✅ **已预留 - 比分预测**
```python
class ScorePredictionService:
    """比分预测（未来扩展）"""
    async def predict_score(self, match: Match) -> ScorePrediction
```

#### ✅ **已预留 - 让球盘预测**
```python
class HandicapPredictionService:
    """让球盘预测（未来扩展）"""
    async def predict_handicap(self, match: Match) -> HandicapPrediction
```

#### ✅ **已预留 - 投注建议**
```python
class BettingAdvisorService:
    """投注建议（未来扩展）"""
    async def advise(self, match: Match, user_risk_profile: str) -> BettingAdvice
```

#### ✅ **已预留 - 用户画像**
```python
class UserProfileService:
    """用户画像（未来扩展）"""
    async def build_profile(self, user_id: str) -> UserProfile
    async def update_from_interaction(self, user_id: str, interaction: Interaction)
```

#### ✅ **已预留 - A/B测试框架**
```python
class ABTestFramework:
    """A/B测试框架（未来扩展）"""
    def assign_bucket(self, user_id: str, experiment: str) -> str
    async def log_metric(self, user_id: str, metric: str, value: float)
```

---

## 五、MVP实施计划（2周）

### Week 1: 核心框架

#### Day 1-2: 对话引擎基础
- [x] ReasoningEngine（已完成）
- [x] DataAnalyzer（已完成）
- [ ] IntentClassifier（基于规则+LLM）
- [ ] EntityRecognizer（基于规则+映射库）
- [ ] ContextManager（基于内存存储）

#### Day 3-4: 业务场景
- [ ] PredictionScenario（预测场景）
- [ ] AnalysisScenario（分析场景）
- [ ] QueryScenario（查询场景）

#### Day 5-7: 服务实现
- [ ] PredictionService（集成现有XGBoost模型）
- [ ] AnalysisService（集成ReasoningEngine）
- [ ] DataService（优化数据访问）

### Week 2: 集成与优化

#### Day 8-9: 系统集成
- [ ] AgentServiceV3（集成所有组件）
- [ ] FallbackStrategy（降级策略）
- [ ] 错误处理与日志

#### Day 10-11: 测试与优化
- [ ] 单元测试
- [ ] 场景测试（9大场景逐一验证）
- [ ] 性能优化

#### Day 12-14: 用户测试与迭代
- [ ] 邀请10人测试
- [ ] 收集反馈
- [ ] 快速迭代优化

---

## 六、与现有代码的关系

### 6.1 复用已有组件

✅ **保留并增强**:
- `src/agent/core/reasoning_engine.py` - 推理引擎
- `src/agent/core/data_analyzer.py` - 数据分析器
- `src/agent/core/planner.py` - 作为IntentClassifier的基础
- `src/agent/tools/` - 所有工具继续使用

### 6.2 重构组件

🔄 **重构优化**:
- `src/services/api/services/agent_v2.py` → `agent_service_v3.py`
- `src/agent/orchestrator.py` → `business_orchestrator.py`（增强场景路由）

### 6.3 新增组件

✨ **新创建**:
- `src/agent/dialog/` - 对话引擎模块
- `src/agent/scenarios/` - 业务场景模块
- `src/agent/services/` - 业务服务模块

---

## 七、配置化设计

所有业务策略都应该可配置：

```yaml
# config/agent_v3.yaml

dialog:
  intent_classifier:
    confidence_threshold: 0.7
    fallback_to_llm: true

  context_manager:
    ttl_seconds: 300
    max_history: 5

prediction:
  default_phase: "T-24h"
  confidence_threshold: 0.6
  model_health_check_interval: 3600

recommendation:
  top_k: 5
  diversity_weight: 0.3
  ranking_weights:
    interest: 0.4
    excitement: 0.3
    importance: 0.2
    convenience: 0.1

fallback:
  max_retries: 2
  timeout_seconds: 2
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

---

## 八、监控与质量保证

### 8.1 关键指标

**对话质量**:
- 意图识别准确率 > 90%
- 实体识别准确率 > 95%
- 上下文引用正确率 > 85%

**预测质量**:
- 预测准确率 > 60%
- 概率校准误差 < 0.1
- 预测覆盖率 > 95%

**推荐质量**:
- 推荐点击率 > 30%
- 用户满意度 > 4.0/5.0
- 推荐多样性 > 0.7

**系统性能**:
- 响应时间 P95 < 2s
- 服务可用性 > 99.5%
- 降级触发率 < 1%

### 8.2 日志与监控

```python
# 每次对话都记录
logger.info({
    "session_id": session_id,
    "intent": intent,
    "entities": entities,
    "scenario": scenario,
    "response_time": response_time,
    "fallback": is_fallback,
    "user_satisfaction": user_rating
})
```

---

## 总结

这个架构设计：

1. ✅ **符合PDF文档要求** - 9大场景、容错降级、可解释性
2. ✅ **模块化可扩展** - 插件化设计，方便后期扩展
3. ✅ **复用现有代码** - ReasoningEngine、DataAnalyzer等核心组件
4. ✅ **业务优先** - 每个模块都对应明确的业务价值
5. ✅ **可配置** - 业务策略都可通过配置调整
6. ✅ **可监控** - 关键指标清晰，便于质量保证

**下一步**: 开始实施MVP（2周计划）
