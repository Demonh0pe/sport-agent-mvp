# Sport Agent MVP

面向企业级智能体育平台的 MVP，实现「赛前预测 + 智能解读 + 资讯聚合 + Agent 交互」能力。

## 特性概览
- FastAPI 服务：`/api/v1/prediction`, `/api/v1/news`, `/api/v1/agent`。
- 伪数据回填，方便前端/Agent 调试；后续可对接真实特征仓与模型。
- 统一配置（`config/`）、目录结构（参考 `docs/sport-agent-tech-design.md`）。

## 快速开始
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn src.services.api.main:app --reload --port 8080
```

访问 `http://localhost:8080/docs` 查看 Swagger。

## 目录说明
- `docs/`：
  - `sport-agent-tech-design.md` 技术设计
  - `tech-stack.md` 技术选型
  - `agent-design.md` Agent 架构
  - `project-initial-plan.md` 初期交付计划与里程碑
- `src/`：
  - `services/api` FastAPI 入口、路由、服务
  - `shared` 配置等共用模块
  - 其余目录为特征、模型、管道占位
- `config/`：数据库、特征仓、模型、服务、Agent 工具配置
- `pipelines/`：Airflow DAG、notebook 占位
- `infra/`：Terraform/K8s 占位

## 环境变量
- `.env`（可选）：支持 `SPORT_AGENT__` 前缀覆写配置，如 `SPORT_AGENT__SERVICE__API__PORT=9000`。

## 后续规划
- 打通数据管道与 Feature Store，替换预测伪逻辑。
- 接入真实资讯来源 + 情感分析。
- 完善 Agent Planner/Executor，支持 match resolver & 策略工具。
- 构建监控与告警 Dashboard（`monitoring/`）。
