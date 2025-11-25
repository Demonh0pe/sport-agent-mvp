# Sport Agent 智能体育平台技术设计文档（MVP v1.0）

> 宗旨：面向企业级智能体育平台（定位类似智能化虎扑），聚焦“数据驱动的预测 + 多模态资讯理解 + Agent 智能交互”三大核心能力，交付可扩展的 MVP 底座。

## 目录
1. [执行摘要与范围](#执行摘要与范围)
2. [产品定位与核心场景](#产品定位与核心场景)
3. [总体架构](#总体架构)
4. [数据与知识层设计](#数据与知识层设计)
5. [AI/ML 与智能体层设计](#aiml-与智能体层设计)
6. [服务接口与体验层](#服务接口与体验层)
7. [平台工程与治理](#平台工程与治理)
8. [实施路线与里程碑](#实施路线与里程碑)
9. [目录结构建议](#目录结构建议)

---

## 执行摘要与范围
- **业务目标**：在 12 周内上线面向 C 端球迷 & 行业分析师的智能体育 MVP，提供“赛前预测 + 智能解读 + 实时资讯”组合能力，满足对话式问答、资讯订阅、策略推荐等上层产品快速迭代需求。
- **技术目标**：建设统一数据底座、特征与模型服务、可插拔多工具 Agent 框架，并以 API 形式对外供给。
- **范围（MVP）**：
  1. 五大联赛近 3 赛季内的**赛前胜平负预测**与解释；
  2. 官方数据 + 资讯抓取 + 社媒信号的**结构化建模与质检**；
  3. 基于多工具 Agent 的**预测/资讯/策略多轮交互 API**；
  4. 基础内容生成（赛事解读、趋势摘要）与推荐支撑接口。

成功标准：预测 LogLoss 较简单赔率基线提升≥8%，资讯延迟≤5 min，Agent 对话命中率（用户问题成功回答）≥90%，平台 SLA 99.5%。

---

## 产品定位与核心场景

### 用户画像
- **球迷用户**：希望快速获得可信赖的赛前观点、资讯、推荐话题。
- **体育媒体/编辑**：批量生产预测稿/解读稿，追踪冷门信号。
- **内部策略/推荐系统**：调用统一预测/资讯 API 组合自有体验。

### MVP 核心场景
1. **赛前智能问答**：“这场谁会赢？为什么？” → 返回概率、关键因素、可信度提示。
2. **多源资讯聚合**：比赛、球队、球员相关的官方伤停、社媒热度、赔率波动 → 以结构化指标 + 文本摘要输出。
3. **Agent 交互**：支持“预测工具 + 资讯工具 + 策略工具”协作，用户可追问或指定策略（如保守下注）。
4. **趋势订阅**：基于用户关注球队/玩法的推送（MVP 输出接口，前端可延后）。

---

## 总体架构

```
┌────────────────────────────────────────────────────────┐
│ 体验层：Web / App / 对话Agent / 推荐系统 / 内部工具        │
└──────────────▲───────────────────────┬──────────────────┘
               │API Gateway (REST/GraphQL) │Event Bus (Kafka)
┌──────────────┴───────────────────────▼──────────────────┐
│ 服务层：比赛服务｜预测服务｜资讯服务｜Agent Orchestrator │
├────────────────────────────────────────────────────────┤
│ 智能层：特征仓｜模型服务 (XGB, Elo, LLM)｜向量检索｜工具库 │
├────────────────────────────────────────────────────────┤
│ 数据层：Raw Lake｜关系库 (PostgreSQL)｜Feature Store｜KG │
├────────────────────────────────────────────────────────┤
│ 采集/管道：官方接口、第三方数据、资讯爬虫、社媒监听       │
└────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                           平台层：CI/CD、监控、权限、安全
```

- **分层思路**：数据层负责“可信数据 + 特征”；智能层提供预测/检索/生成；服务层封装领域 API 与 Agent 调度；体验层自由组合。
- **多工具 Agent**：Orchestrator 维护工具注册表（预测、资讯检索、赔率计算、策略建议），通过 Planner/Executor 机制在一次对话中多次调用。

---

## 数据与知识层设计

### 数据来源
1. **官方数据**：比赛、实时比分、阵容；通过付费 API（Opta、StatsBomb）或授权 Feed。
2. **赔率与市场**：主流博彩公司的盘口/隐含概率，用于基线/特征。
3. **资讯与伤停**：RSS、新闻站点、俱乐部官宣；采用爬虫 + NLP 摘要。
4. **社媒/社区信号**：Twitter/X、Reddit、虎扑等，提取热度与情绪指数。

### 存储策略
- **Raw Lake (S3/OSS)**：保存原始 JSON/CSV/HTML，按数据源+日期分区。
- **关系库（PostgreSQL）**：承载 `league`, `team`, `match`, `match_stats`, `team_stats`, `h2h`, `news`, `social_signal` 等核心实体。
- **Feature Store**：`feature_store.match_features`（按 `match_id`, `phase` 分区）、`team_snapshot`、`player_snapshot`，采用 DuckDB/Parquet + Redis 缓存。
- **知识图谱 (Neo4j / Neptune)**：节点（联赛、球队、球员、比赛、资讯），边表示关系（参加、对战、伤病影响、资讯引用）；Agent 可基于 KG 检索关系解释。

### 数据建模补充
- **资讯表**：`news_id`, `entity_type`, `entity_id`, `source`, `sentiment`, `reliability_score`, `published_at`, `content_vector`。
- **社媒信号表**：`signal_id`, `entity_id`, `volume_index`, `sentiment_score`, `anomaly_score`。
- **赔率表**：`bookmaker`, `odds_type`, `implied_prob_*`, `last_updated`，支持时序分析。

### 数据治理 & QA
- Schema Registry 管理各数据源版本。
- Airflow DAG：`ingest_*` → `validate_*` → `normalize_*` → `feature_build`。
- QA 规则：
  - 完整性：关键字段缺失率实时监控；
  - 一致性：比分 vs `result_1x2`、控球率和≈100%；
  - 延迟：资讯延迟 SLA 5 分钟，超时报警；
  - 异常检测：使用统计 + ML（如 Isolation Forest）识别异常赔率波动或社媒暴涨。

---

## AI/ML 与智能体层设计

### 预测与评分引擎
- **模型组合**：
  - `XGB_match_outcome_v1`：多分类胜平负；
  - `Elo_diff_baseline`：提供 fallback 与可解释评分；
  - `InjuryImpactModel`：资讯向量 → 影响指数，用于特征校正；
  - `MomentumScorer`：时间序列趋势（ARIMA/Prophet + 规则）。
- **训练流水线**：`feature_store` → `model_train`（MLflow 追踪）→ `model_validate`（Accuracy/LogLoss/Brier）→ `model_registry`。
- **推理服务**：基于 BentoML/Sagemaker Endpoint，支持 A/B、Shadow 流量。

### 资讯理解与内容生成
- **Retrieval**：向量库（FAISS/PgVector）按实体聚合资讯，支持时间窗过滤。
- **NLP 管道**：实体识别、情感分析、谣言检测（规则+模型）、事件抽取（伤病、转会、教练变动）。
- **生成**：LLM（例如 GPT-4o-mini 或自建 Llama）+ 提示模板，输出预测解释、资讯摘要、策略建议；使用 Guardrail 检查事实性。

### 多工具 Agent 架构
- **Planner**：基于 ReAct + 规则，识别意图（预测/资讯/混合），规划所需工具（PredictionTool, NewsTool, OddsTool, StrategyTool）。
- **Executor**：顺序或并行调用，写入 `conversation_trace`，供调试与用户追溯。
- **记忆层**：短期上下文（对话历史）、长期偏好（用户画像、关注球队），存储于 Redis + Postgres。
- **工具规范**：
  - `PredictionTool(match_id, phase)` → 概率/解释；
  - `NewsTool(entity_id, window)` → 最新资讯列表 + 摘要；
  - `OddsTool(match_id)` → 盘口对比 + 异常提示；
  - `StrategyTool(preference)` → 根据风险偏好输出建议。

### 监控与模型治理
- 离线：每周性能报告（分联赛 Accuracy、LogLoss、资讯召回）；
- 在线：Prometheus + Grafana 监控推理延迟、错误率、Agent 工具调用失败率；
- Drift 探测：统计特征分布、KS 检验，触发再训练；
- 模型治理：MLflow + Model Registry + 审批流程，版本发布需通过自动化评测。

---

## 服务接口与体验层

### API 设计
- **Gateway**：Kong / APISIX，支持 JWT/OAuth2、配额、流控。
- **REST/GraphQL**：
  - `GET /api/v1/match/{match_id}`：比赛基础信息 + 赛程；
  - `GET /api/v1/prediction/{match_id}`：概率、置信度、模型版本、冷启动标记；
  - `GET /api/v1/prediction/{match_id}/explain`：结构化解释（因素、贡献度、引用资讯 ID）；
  - `GET /api/v1/news`：按实体/时间过滤，返回资讯摘要、情绪、可信度；
  - `POST /api/v1/agent/query`：输入自然语言，返回 Agent 推理轨迹 + 最终回答；
  - `GET /api/v1/recommendation/feed`（MVP 输出接口，供前端订阅）。

### 事件与订阅
- Kafka 主题：`match_updates`, `prediction_results`, `news_ingested`, `agent_feedback`。
- Webhook：当预测置信度变化、资讯触发阈值时通知业务系统。

### 前端/体验对接（参考）
- 对话式 UI：显示预测结论 + 解释卡片 + 资讯引用。
- 数据看板：预测模型表现、资讯延迟、Agent 工具调用可视化。

---

## 平台工程与治理

### DevOps
- **CI/CD**：GitHub Actions → 单元/集成测试 → SonarQube → Docker 构建 → ArgoCD 部署。
- **环境**：`dev`（沙盒数据）、`staging`（准生产，匿名化真实数据）、`prod`。
- **配置管理**：`config/` + Vault，敏感凭据统一托管。

### 安全与合规
- 数据加密：静态（KMS）+ 传输（TLS）；
- 访问控制：RBAC + ABAC，细化到服务/表/列；
- 合规：确保资讯版权授权，存档用户查询与模型输出以备审计；
- 隐私：对社媒数据做匿名化/脱敏。

### 可观测性
- 日志：结构化 JSON，集中在 ELK/Opensearch；
- 指标：预测延迟、Agent 调用耗时、资讯抓取延迟；
- Tracing：OpenTelemetry 贯穿 API → 服务 → 模型；
- 报警：OpsGenie/Slack，支持分级响应（P1~P3）。

---

## 实施路线与里程碑

| 阶段 | 周期 | 关键成果 | 核心交付 |
| --- | --- | --- | --- |
| M0 平台准备 | 第 1–2 周 | 数据接入、Infra、CI/CD、Observability 框架 | Infra as Code、Airflow、监控基线 |
| M1 数据 & 特征 | 第 3–6 周 | ER & Schema、核心数据管道、Feature Store v1 | `schema.sql`, `ingest` DAG, `feature_store.match_features` |
| M2 模型 & 资讯 | 第 7–9 周 | XGBoost Baseline、Elo fallback、资讯解析/摘要 | `model_registry/xgb_v1`, `news_pipeline`, 评估报告 |
| M3 Agent & API | 第 10–12 周 | FastAPI 服务、Agent Orchestrator、对话/REST API、监控 | `src/services`, `agent_orchestrator`, SLA Dashboard |

加速项：并行推进前端 POC；准备多联赛扩容方案（数据分区 + 模型多租户）；为后续玩法扩展（让球/大小球/事件预测）预留模型接口。

---

## 目录结构建议
```
sport-agent/
  infra/
    terraform/
    k8s/
  data/
    raw/
    processed/
    features/
  db/
    schema.sql
    migrations/
  pipelines/
    airflow_dags/
    notebooks/
      EDA.ipynb
      feature_engineering.ipynb
      news_nlp.ipynb
      model_train_xgb.ipynb
  src/
    data_pipeline/
    feature_store/
    models/
      prediction/
      baseline/
    services/
      api/
      agent/
      news/
    shared/
  config/
    db.yaml
    feature_store.yaml
    model.yaml
    service.yaml
    agent_tools.yaml
  docs/
    sport-agent-tech-design.md
  model_registry/
    xgb_match_outcome_v1/
  monitoring/
    dashboards/
    alerts/
```

---

*本技术文档立足企业级场景，聚焦 MVP 期的“预测 + 资讯 + Agent”闭环，并为后续多玩法扩展、社区化运营、商业化模块预留架构空间。*
