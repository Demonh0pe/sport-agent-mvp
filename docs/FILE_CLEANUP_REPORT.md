# 项目文件清理报告

## 📊 当前状态

**总文件数**: 约 120+ 个文件  
**总目录数**: 约 40+ 个目录  
**项目规模**: 中等（测试阶段偏大）

---

## 🗑️ 可以删除的文件/目录

### 1. 重复/过时的数据摄取脚本

#### ❌ 可删除
```bash
src/data_pipeline/ingest_football_data.py  # 旧版本，已被 v2 替代
```

**原因**: 
- `ingest_football_data_v2.py` 是改进版，功能更完善
- 保留两个版本容易混淆

**操作**:
```bash
rm src/data_pipeline/ingest_football_data.py
```

---

### 2. 临时测试文件

#### ❌ 可删除（或移到 tests/ 目录）
```bash
test_llm.py                           # 根目录的临时测试
evaluate_planner.py                   # 临时评估脚本
scripts/quick_test.py                 # 快速测试脚本
scripts/test_liverpool_standing.py    # 临时测试
scripts/check_finished_matches.py     # 临时检查脚本
scripts/check_match_status.py         # 临时检查脚本
```

**建议操作**:
```bash
# 1. 创建 tests/manual/ 目录存放手动测试
mkdir -p tests/manual

# 2. 移动文件
mv test_llm.py tests/manual/
mv evaluate_planner.py tests/manual/
mv scripts/quick_test.py tests/manual/
mv scripts/test_liverpool_standing.py tests/manual/
mv scripts/check_finished_matches.py tests/manual/
mv scripts/check_match_status.py tests/manual/

# 3. 或者直接删除（如果不需要）
rm test_llm.py evaluate_planner.py scripts/quick_test.py
```

---

### 3. 空目录/未使用的基础设施

#### ❌ 可删除（暂时不需要）
```bash
infra/k8s/                    # Kubernetes 配置（测试阶段不需要）
infra/terraform/              # Terraform 配置（测试阶段不需要）
monitoring/alerts/            # 监控告警（测试阶段不需要）
monitoring/dashboards/        # 监控面板（测试阶段不需要）
model_registry/               # 模型注册表（还没有模型）
pipelines/notebooks/          # Jupyter notebooks（空目录）
data/features/                # 特征数据（空目录）
data/processed/               # 处理后数据（空目录）
data/raw/                     # 原始数据（空目录）
```

**建议操作**:
```bash
# 暂时删除，需要时再创建
rm -rf infra/k8s infra/terraform
rm -rf monitoring/alerts monitoring/dashboards
rm -rf model_registry
rm -rf pipelines/notebooks
rm -rf data/features data/processed data/raw
```

---

### 4. 未使用的配置文件

#### ⚠️ 可选删除
```bash
config/agent_tools.yaml       # 工具配置（目前在代码中硬编码）
config/feature_store.yaml     # 特征存储（还未实现）
config/model.yaml             # 模型配置（还未实现）
db/migrations/                # 空目录（使用 alembic）
db/schema.sql                 # 只有 1 行，基本无用
```

**建议操作**:
```bash
# 备份后删除
rm config/agent_tools.yaml config/feature_store.yaml config/model.yaml
rm -rf db/migrations
rm db/schema.sql
```

---

### 5. 重复/过时的文档

#### ⚠️ 可归档
```bash
docs/Agent设计文档.md         # 中文版，与英文版重复
docs/project-initial-plan.md  # 初始计划，已过时
docs/agent-design.md          # 旧设计文档
```

**建议操作**:
```bash
# 创建 docs/archive/ 目录
mkdir -p docs/archive

# 移动旧文档
mv docs/Agent设计文档.md docs/archive/
mv docs/project-initial-plan.md docs/archive/
mv docs/agent-design.md docs/archive/
```

---

### 6. 扩展模型文件（暂未使用）

#### ⚠️ 可选删除
```bash
src/infra/db/models_extended.py  # 扩展模型（目前已合并到 models.py）
```

**建议操作**:
```bash
# 如果 Standing 已经在 models.py 中，可以删除
rm src/infra/db/models_extended.py
```

---

### 7. 未使用的服务模块

#### ⚠️ 暂时保留（但可精简）
```bash
src/services/agent/           # 空目录
src/services/news/            # 空目录
src/feature_store/            # 空目录
src/models/baseline/          # 空目录
src/models/prediction/        # 空目录
```

**建议操作**:
```bash
# 删除空目录
rm -rf src/services/agent src/services/news
rm -rf src/feature_store
rm -rf src/models/baseline src/models/prediction
```

---

## ✅ 核心文件（必须保留）

### 1. 配置文件
```
config/service.yaml           ✅ 核心配置
config/db.yaml                ✅ 数据库配置
requirements.txt              ✅ 依赖管理
pyproject.toml                ✅ 项目配置
alembic.ini                   ✅ 数据库迁移
docker-compose.yaml           ✅ 容器编排
```

### 2. 数据库相关
```
src/infra/db/models.py        ✅ 数据模型（包含 Standing）
src/infra/db/session.py       ✅ 数据库连接
alembic/versions/             ✅ 数据库迁移历史
```

### 3. 数据管道
```
src/data_pipeline/
  ├── ingest_football_data_v2.py     ✅ 主要数据摄取
  ├── ingest_extended_data.py        ✅ 扩展数据摄取
  ├── entity_resolver.py             ✅ 实体对齐
  ├── data_quality_monitor.py        ✅ 数据质量监控
  └── schemas.py                     ✅ API 响应模型
```

### 4. Agent 核心
```
src/agent/
  ├── core/
  │   ├── planner.py                 ✅ 规划器
  │   ├── executor.py                ✅ 执行器
  │   └── parameter_resolver.py      ✅ 参数解析
  ├── tools/
  │   ├── match_tool.py              ✅ 比赛工具
  │   ├── stats_tool.py              ✅ 统计工具
  │   └── standings_tool.py          ✅ 积分榜工具
  ├── orchestrator.py                ✅ 编排器
  └── prompts/                       ✅ 提示词管理
```

### 5. API 服务
```
src/services/api/
  ├── main.py                        ✅ FastAPI 入口
  ├── dependencies.py                ✅ 依赖注入
  ├── routers/
  │   └── agent.py                   ✅ Agent 路由
  ├── schemas/
  │   └── agent.py                   ✅ API 模型
  └── services/
      ├── agent.py                   ✅ Agent V1
      └── agent_v2.py                ✅ Agent V2（主要）
```

### 6. 工具脚本
```
scripts/
  ├── seed_db.py                     ✅ 数据初始化
  ├── seed_leagues.py                ✅ 联赛初始化
  ├── check_data_count.py            ✅ 数据统计
  ├── run_all_tests.py               ✅ 测试套件
  ├── test_agent_v2.py               ✅ Agent 测试
  ├── test_standings_tool.py         ✅ 工具测试
  └── test_stats_tool.py             ✅ 工具测试
```

### 7. 文档
```
docs/
  ├── HARDCODE_AUDIT.md              ✅ 硬编码审计
  ├── DATA_EXPANSION_SUMMARY.md      ✅ 数据扩展总结
  ├── data-expansion-plan.md         ✅ 扩展计划
  ├── data-pipeline-guide.md         ✅ 数据管道指南
  ├── TESTING_GUIDE.md               ✅ 测试指南
  └── agent-v2-integration-summary.md ✅ Agent V2 总结
```

---

## 🎯 清理建议（按优先级）

### 立即执行（安全删除）

```bash
# 1. 删除旧版本数据摄取脚本
rm src/data_pipeline/ingest_football_data.py

# 2. 删除临时测试文件
rm test_llm.py evaluate_planner.py
rm scripts/quick_test.py

# 3. 删除空目录
rm -rf infra/k8s infra/terraform
rm -rf monitoring
rm -rf model_registry
rm -rf pipelines/notebooks
rm -rf data/features data/processed data/raw
rm -rf db/migrations
rm db/schema.sql

# 4. 删除空服务目录
rm -rf src/services/agent src/services/news
rm -rf src/feature_store
rm -rf src/models

# 5. 删除未使用的配置
rm config/agent_tools.yaml config/feature_store.yaml config/model.yaml
```

**节省空间**: 约 30-40% 的目录  
**风险**: 低（都是空目录或未使用的文件）

---

### 本周执行（建议归档）

```bash
# 1. 创建归档目录
mkdir -p docs/archive tests/manual

# 2. 归档旧文档
mv docs/Agent设计文档.md docs/archive/
mv docs/project-initial-plan.md docs/archive/
mv docs/agent-design.md docs/archive/

# 3. 移动临时测试到专门目录
mv scripts/test_liverpool_standing.py tests/manual/
mv scripts/check_finished_matches.py tests/manual/
mv scripts/check_match_status.py tests/manual/

# 4. 删除扩展模型文件（如果已合并）
# 先确认 Standing 已在 models.py 中
grep "class Standing" src/infra/db/models.py && rm src/infra/db/models_extended.py
```

**节省空间**: 约 10% 的文件  
**风险**: 低（归档不是删除）

---

### 可选执行（评估后决定）

```bash
# 1. 删除旧 Agent Service（如果 V2 稳定）
# rm src/services/api/services/agent.py  # 保留作为参考

# 2. 精简路由（如果不需要）
# rm src/services/api/routers/news.py
# rm src/services/api/routers/prediction.py

# 3. 精简 schemas（如果不需要）
# rm src/services/api/schemas/news.py
# rm src/services/api/schemas/prediction.py
```

---

## 📊 清理后的项目结构

```
sport-agent-mvp/
├── config/                   # 配置文件（精简到 2 个）
│   ├── service.yaml
│   └── db.yaml
├── docs/                     # 文档（8 个核心文档）
│   ├── archive/              # 归档旧文档
│   └── *.md
├── scripts/                  # 工具脚本（7 个核心脚本）
├── src/
│   ├── agent/                # Agent 核心
│   ├── data_pipeline/        # 数据管道（5 个文件）
│   ├── infra/db/             # 数据库（2 个文件）
│   ├── services/api/         # API 服务
│   └── shared/               # 共享模块
├── tests/
│   ├── data/                 # 测试数据
│   └── manual/               # 手动测试脚本
├── alembic/                  # 数据库迁移
├── requirements.txt
├── pyproject.toml
└── docker-compose.yaml
```

**文件数**: 从 120+ 减少到约 60-70  
**目录数**: 从 40+ 减少到约 20  
**清晰度**: 大幅提升 📈

---

## 🚀 快速清理脚本

创建 `scripts/cleanup.sh`:

```bash
#!/bin/bash
# 项目清理脚本

echo "开始清理项目..."

# 1. 删除旧文件
echo "删除旧版本数据摄取脚本..."
rm -f src/data_pipeline/ingest_football_data.py

# 2. 删除临时测试
echo "删除临时测试文件..."
rm -f test_llm.py evaluate_planner.py scripts/quick_test.py

# 3. 删除空目录
echo "删除空目录..."
rm -rf infra/k8s infra/terraform
rm -rf monitoring model_registry pipelines/notebooks
rm -rf data/features data/processed data/raw
rm -rf db/migrations
rm -f db/schema.sql

# 4. 删除空服务目录
echo "删除空服务目录..."
rm -rf src/services/agent src/services/news src/feature_store src/models

# 5. 删除未使用配置
echo "删除未使用配置..."
rm -f config/agent_tools.yaml config/feature_store.yaml config/model.yaml

# 6. 创建归档目录
echo "创建归档目录..."
mkdir -p docs/archive tests/manual

# 7. 归档旧文档
echo "归档旧文档..."
mv -f docs/Agent设计文档.md docs/archive/ 2>/dev/null
mv -f docs/project-initial-plan.md docs/archive/ 2>/dev/null
mv -f docs/agent-design.md docs/archive/ 2>/dev/null

# 8. 移动临时测试
echo "移动临时测试..."
mv -f scripts/test_liverpool_standing.py tests/manual/ 2>/dev/null
mv -f scripts/check_finished_matches.py tests/manual/ 2>/dev/null
mv -f scripts/check_match_status.py tests/manual/ 2>/dev/null

# 9. 删除扩展模型（如果已合并）
if grep -q "class Standing" src/infra/db/models.py; then
    echo "Standing 已在 models.py 中，删除扩展文件..."
    rm -f src/infra/db/models_extended.py
fi

echo "清理完成！"
echo "建议运行: git status 查看变更"
```

**使用方法**:
```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh
```

---

## 📋 清理清单

- [ ] 删除旧版本数据摄取脚本
- [ ] 删除临时测试文件
- [ ] 删除空目录和未使用的基础设施
- [ ] 删除空服务目录
- [ ] 删除未使用的配置文件
- [ ] 归档旧文档
- [ ] 移动临时测试到专门目录
- [ ] 运行 `git status` 检查变更
- [ ] 提交清理后的代码

---

## 💡 长期维护建议

1. **定期清理**: 每月执行一次清理
2. **测试文件规范**: 所有临时测试放到 `tests/manual/`
3. **文档归档**: 旧文档及时移到 `docs/archive/`
4. **空目录清理**: 不要提交空目录
5. **配置精简**: 只保留实际使用的配置文件

---

## 总结

**当前状态**: 测试阶段的项目规模偏大，包含很多未使用的文件  
**清理后**: 精简 40-50% 的文件，项目结构更清晰  
**风险**: 低（主要删除空目录和临时文件）  
**收益**: 提升代码可维护性和可读性  

**建议**: 立即执行安全删除，本周完成归档整理！

