# 技术选型说明（MVP v1.0）

## 目标
- 支撑企业级智能体育平台 MVP（预测 + 资讯 + Agent）。
- 保证数据可信、模型可迭代、服务可观测、Agent 可扩展。

## 分层与选型
### 数据采集与存储
- **数据湖**：S3/OSS（Parquet/JSON），用于原始数据留存。
- **数据库**：PostgreSQL（OLTP + 分析分区）、Redis（缓存）、Neo4j/Neptune（知识图谱）。
- **消息总线**：Kafka，用于赛事更新、资讯推送、预测结果事件。

### 计算与特征
- **ETL/编排**：Airflow（Python DAG）+ dbt/SQL 转换。
- **批处理**：Pandas/Polars、DuckDB；必要时 Spark-on-Lake。
- **Feature Store**：自建 Parquet + Redis 缓存，按 `match_id + phase` 分区。

### 模型与推理
- **建模框架**：XGBoost、LightGBM、scikit-learn；MLflow 追踪与注册。
- **服务化**：BentoML/SageMaker Endpoint，支持 A/B、Shadow。
- **可解释性**：SHAP、LightGBM 内置重要性、Elo 基线参考。

### 服务与接口
- **API 框架**：FastAPI + Uvicorn；Pydantic v2 Schema。
- **网关/安全**：Kong/APISIX、JWT/OAuth2、OPA 或自研 RBAC。
- **缓存**：Redis（预测结果 1h TTL、资讯 5min）。
- **监控**：Prometheus + Grafana；日志 ELK；Trace 用 OpenTelemetry。

### Agent 与应用层
- **Agent Orchestrator**：Python + LangChain/LlamaIndex（可选），Planner/Executor 结合规则与 LLM。
- **LLM/生成**：OpenAI GPT-4o-mini / Azure OpenAI / 本地 Llama3.1，根据安全策略切换。
- **向量检索**：FAISS/PgVector，支撑资讯检索与记忆。

### 工程与 DevOps
- **配置**：pydantic-settings + Vault。
- **CI/CD**：GitHub Actions + Sonar + ArgoCD/K8s。
- **容器化**：Docker + 多阶段构建；K8s for prod。
- **IaC**：Terraform（底层资源）+ Helm/Kustomize（部署）。

## 选型理由摘要
- 以 Python 生态为主，方便数据、模型、Agent 统一栈。
- 采用 FastAPI/MLflow/BentoML 等成熟组件，兼顾开发效率与可运维性。
- 通过 Kafka、Feature Store、Neo4j 等扩展，保证后续多源数据与智能交互需求。
