# 数据管道使用指南

## 📚 概述

本文档介绍如何使用改进版的 Football-data.org 数据摄取管道。

## 🎯 核心特性

### ✅ v2.0 新增功能

1. **自动实体对齐** - 使用 `EntityResolver` 自动匹配球队名称
2. **智能重试机制** - 使用 `tenacity` 实现指数退避重试
3. **多联赛支持** - 支持五大联赛 + 欧冠
4. **增量更新** - 只拉取最近变化的数据
5. **数据质量检查** - 自动检测异常数据
6. **Airflow 调度** - 自动化定时任务
7. **监控告警** - 实时数据质量监控

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 或使用 poetry
poetry install
```

### 2. 配置 API Key

编辑 `config/service.yaml`:

```yaml
data_source:
  football_data_org:
    base_url: "https://api.football-data.org/v4"
    api_key: "YOUR_API_KEY_HERE"  # 从 https://www.football-data.org/client/register 获取
```

**或** 使用环境变量:

```bash
export SPORT_AGENT__DATA_SOURCE__FOOTBALL_DATA_ORG__API_KEY="your_key_here"
```

### 3. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 播种初始球队数据
python scripts/seed_db.py
```

### 4. 运行数据摄取

#### 方式 1: 手动运行（推荐用于测试）

```bash
# 运行改进版摄取脚本
python src/data_pipeline/ingest_football_data_v2.py
```

#### 方式 2: 使用 Airflow（推荐用于生产）

```bash
# 启动 Airflow
airflow webserver --port 8080 &
airflow scheduler &

# 访问 UI: http://localhost:8080
# 手动触发 DAG: football_data_daily_full_sync
```

---

## 📊 数据质量监控

### 运行质量检查

```bash
python src/data_pipeline/data_quality_monitor.py
```

### 输出示例

```
📊 数据质量监控报告
============================================================
⏰ 检查时间: 2025-11-24T08:00:00Z
🏥 健康状态: HEALTHY
⚠️  告警数量: 0

📈 关键指标:
  - 总比赛数: 156
  - 最后更新: 0.5 小时前
  - 未来7天比赛: 23 场

✅ 无告警信息，数据质量良好！
============================================================
```

---

## 🔧 高级配置

### 自定义实体对齐规则

编辑 `src/data_pipeline/entity_resolver.py`:

```python
# 添加自定义别名
self._team_cache["man utd"] = "MUN"
self._team_cache["红魔"] = "MUN"
```

### 调整重试策略

编辑 `src/data_pipeline/ingest_football_data_v2.py`:

```python
@retry(
    stop=stop_after_attempt(5),  # 最多重试5次
    wait=wait_exponential(multiplier=2, min=4, max=60),  # 指数退避
)
async def _fetch_matches(...):
    ...
```

### 配置增量更新窗口

```python
await ingester.ingest_league(
    league_code="PL",
    incremental=True,
    days_back=14  # 回溯14天
)
```

---

## 📋 API 配额管理

### Football-data.org 免费计划限制

- **请求频率**: 10 次/分钟
- **每日请求**: 无限制（但有频率限制）
- **覆盖联赛**: 免费计划仅支持部分联赛

### 付费计划对比

| 计划 | 价格 | 请求频率 | 覆盖联赛 |
|-----|-----|---------|---------|
| Free | $0 | 10/min | 5+ 联赛 |
| Tier 1 | €19/月 | 60/min | 全部联赛 |
| Tier 2 | €49/月 | 120/min | 全部+历史 |

**推荐**: MVP 阶段使用免费计划，生产环境升级到 Tier 1。

---

## 🐛 常见问题

### Q1: 如何处理 API 429 错误？

**A**: 脚本已内置重试机制，会自动等待并重试。如果频繁出现，考虑：
- 增加请求间隔
- 升级到付费计划
- 使用缓存减少重复请求

### Q2: 如何添加新的数据源？

**A**: 
1. 在 `src/data_pipeline/schemas.py` 定义数据模型
2. 创建新的摄取脚本 `ingest_[source]_v2.py`
3. 实现 `EntityResolver` 的映射规则
4. 添加 Airflow DAG

### Q3: 数据不一致怎么办？

**A**: 
1. 运行质量监控: `python src/data_pipeline/data_quality_monitor.py`
2. 查看 `data_quality_report.json` 找出问题数据
3. 手动修正或重新摄取

---

## 📈 性能优化建议

### 1. 数据库索引

```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_match_date ON matches(match_date);
CREATE INDEX idx_match_status ON matches(status);
CREATE INDEX idx_match_league_date ON matches(league_id, match_date);
```

### 2. 缓存策略

使用 Redis 缓存频繁查询的数据：

```python
# 缓存球队映射
redis.setex(
    f"team_mapping:{external_name}",
    3600,  # 1小时
    team_id
)
```

### 3. 批量处理

将数据库操作批量提交而非逐条提交：

```python
# 使用批量插入
await db.execute(insert(Match).values(match_list))
await db.commit()
```

---

## 🔗 相关资源

- [Football-data.org API 文档](https://www.football-data.org/documentation/quickstart)
- [Airflow 官方文档](https://airflow.apache.org/docs/)
- [项目技术设计](./sport-agent-tech-design.md)

---

## 📞 支持与反馈

如有问题或建议，请联系：
- 📧 Email: team@sport-agent.com
- 💬 Slack: #data-pipeline 频道

