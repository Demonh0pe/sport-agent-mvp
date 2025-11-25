# 数据真实性审查报告 (Data Authenticity Audit)

**日期**: 2025-11-25  
**严重程度**: 🔴 CRITICAL - 系统中存在虚假测试数据与真实数据混合

---

## 🚨 核心问题

数据库中**混合了两种不同来源的数据**，导致Agent返回虚假信息：

### 1. 虚假数据来源 (Seed Data)

```
Match ID: 2024_EPL_MUN_LIV
日期: 2025-11-21 07:52:43 (UTC)
对阵: 曼联 (MUN) vs 利物浦 (LIV)
比分: 0-3 (主场惨败)
标签: ['Derby', 'Big6', '惨败']
状态: FINISHED
```

**问题**: 这场比赛**不存在**！这是 `scripts/seed_db.py` 创建的测试数据。

### 2. 真实数据来源 (API Data)

```
Match ID: PL_537902
日期: 2025-11-24 20:00:00 (UTC)
对阵: 曼联 (MUN) vs 埃弗顿 (EVE)
比分: 0-1
标签: ['ImportedFromAPI', 'PL']
状态: FINISHED
```

**来源**: 从 football-data.org API 拉取的真实比赛数据。

---

## 📊 数据库现状分析

### 曼联最近10场比赛记录 (按时间倒序)

| Match ID | 日期 | 对阵 | 比分 | 数据源 | 真实性 |
|----------|------|------|------|--------|--------|
| PL_537946 | 2025-12-21 | AVL vs MUN | 未开赛 | API | ✅ 真实 |
| PL_537942 | 2025-12-15 | MUN vs BOU | 未开赛 | API | ✅ 真实 |
| PL_537934 | 2025-12-08 | WOL vs MUN | 未开赛 | API | ✅ 真实 |
| PL_537922 | 2025-12-04 | MUN vs WHU | 未开赛 | API | ✅ 真实 |
| PL_537907 | 2025-11-30 | CRY vs MUN | 未开赛 | API | ✅ 真实 |
| **PL_537902** | 2025-11-24 | **MUN vs EVE** | **0-1** | **API** | ✅ **真实** |
| **2024_EPL_MUN_LIV** | **2025-11-21** | **MUN vs LIV** | **0-3** | **Seed** | ❌ **虚假** |
| PL_537893 | 2025-11-08 | TOT vs MUN | 2-2 | API | ✅ 真实 |
| PL_537882 | 2025-11-01 | NOT vs MUN | 2-2 | API | ✅ 真实 |
| PL_537872 | 2025-10-25 | MUN vs BHA | 4-2 | API | ✅ 真实 |

### 虚假数据的影响范围

#### 测试Agent的输出 (受影响的结果)

**测试1: "曼联对利物浦，谁会赢？"**
```
Agent回答: "在2025年11月21日的最近一次交手中，曼联主场0-3负于利物浦"
```
❌ **这是虚假信息！该比赛不存在。**

**测试5: "曼联最近5场比赛的战绩如何"**
```
- 2025-11-24: 曼联 vs 埃弗顿 (0:1) (负) ✅ 真实
- 2025-11-21: 曼联 vs 利物浦 (0:3) (负) ❌ 虚假
- 2025-11-08: 托特纳姆热刺 vs 曼联 (2:2) (平) ✅ 真实
- 2025-11-01: 诺丁汉森林 vs 曼联 (2:2) (平) ✅ 真实
- 2025-10-25: 曼联 vs 布莱顿 (4:2) (胜) ✅ 真实
```

#### 其他Seed数据记录

```
Match ID: 2024_EPL_ARS_MCI
日期: 未来某天 (动态生成)
对阵: 阿森纳 (ARS) vs 曼城 (MCI)
状态: FIXTURE
标签: ['Title Race', '关键战']
```
❌ **同样是虚假的测试数据**

---

## 🔍 根本原因分析

### 1. `scripts/seed_db.py` 的设计缺陷

**问题代码** (第56-70行):

```python
# 场景 A: 已结束的惨败 (曼联 0:3 利物浦) - 用于测试战报生成
match_finished = Match(
    match_id="2024_EPL_MUN_LIV",
    league_id="EPL",
    home_team_id="MUN",
    away_team_id="LIV",
    # 比赛时间：3天前  ⚠️ 动态时间，不固定
    match_date=datetime.now(timezone.utc) - timedelta(days=3),
    status="FINISHED",
    home_score=0,
    away_score=3,
    result="A",  # Away Win (客队胜)
    tags=["Derby", "Big6", "惨败"]  ⚠️ 没有"TestData"标记
)
```

**问题**:
1. ❌ 使用动态时间 `datetime.now() - timedelta(days=3)`，导致数据与真实API数据的时间重叠
2. ❌ 标签中没有明确标记为"TestData"或"Seed"
3. ❌ 使用了真实球队ID (MUN, LIV)，与真实数据混淆
4. ❌ 没有检查是否与真实API数据冲突

### 2. 数据管道设计缺陷

#### `src/data_pipeline/ingest_football_data_v2.py`

- ✅ 正确标记了API数据: `tags=["ImportedFromAPI", league_code]`
- ❌ 但没有过滤或覆盖Seed数据

#### `src/agent/tools/match_tool.py`

```python
async def get_recent_matches(self, team_name: str, limit: int = 5) -> str:
    # 查询所有FINISHED状态的比赛，按日期降序
    finished_stmt = select(Match).where(
        and_(
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
            Match.status == "FINISHED"
        )
    ).order_by(Match.match_date.desc()).limit(limit)
```

❌ **没有过滤Seed数据** - 直接返回所有FINISHED状态的比赛，不管是否真实。

### 3. 测试数据管理缺失

- ❌ 没有隔离测试环境和生产环境的数据库
- ❌ 没有明确的数据清理策略
- ❌ 没有数据真实性验证机制

---

## 🛠️ 解决方案

### 立即行动 (Critical)

#### 1. 清理虚假数据

```sql
-- 删除所有Seed数据
DELETE FROM matches WHERE tags @> ARRAY['Derby', 'Big6', '惨败'];
DELETE FROM matches WHERE tags @> ARRAY['Title Race', '关键战'];

-- 或者更安全的方式：标记为测试数据
UPDATE matches 
SET tags = tags || ARRAY['__INVALID_SEED_DATA__']
WHERE match_id IN ('2024_EPL_MUN_LIV', '2024_EPL_ARS_MCI');
```

#### 2. 禁用 `scripts/seed_db.py`

```python
# 在文件顶部添加警告
"""
⚠️ 警告: 此脚本已废弃！
该脚本会创建虚假测试数据，导致与真实API数据混淆。
请使用以下替代方案:
1. 测试环境: 使用独立的测试数据库
2. 单元测试: 使用Mock数据 (src/agent/tools/mock_responses.py)
3. 集成测试: 使用 tests/data/golden_dataset.json
"""

async def seed_data():
    raise RuntimeError(
        "此脚本已禁用！请勿在生产环境运行。\n"
        "如需测试数据，请使用独立的测试数据库。"
    )
```

#### 3. 修改 `match_tool.py` - 过滤测试数据

```python
async def get_recent_matches(self, team_name: str, limit: int = 5) -> str:
    # 查询所有FINISHED状态的比赛，按日期降序
    # ✅ 新增: 过滤掉非API来源的数据
    finished_stmt = select(Match).where(
        and_(
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
            Match.status == "FINISHED",
            # 只返回来自API的真实数据
            Match.tags.contains(['ImportedFromAPI'])  
        )
    ).order_by(Match.match_date.desc()).limit(limit)
```

### 短期改进 (High Priority)

#### 4. 实施数据标签规范

所有数据必须明确标记来源:

```python
DATA_SOURCE_TAGS = {
    "API": "ImportedFromAPI",      # 真实API数据
    "SEED": "__SEED_DATA__",        # 测试种子数据
    "MOCK": "__MOCK_DATA__",        # Mock数据（仅用于开发）
    "USER": "UserGenerated",        # 用户自定义数据
}
```

#### 5. 添加数据验证中间件

```python
class DataAuthenticityValidator:
    """数据真实性验证器"""
    
    async def validate_match(self, match: Match) -> bool:
        """
        验证比赛数据的真实性
        
        Returns:
            True if authentic, False otherwise
        """
        # 规则1: 必须有来源标签
        if not match.tags or not any(
            tag in match.tags for tag in ['ImportedFromAPI', 'UserGenerated']
        ):
            logger.warning(f"Match {match.match_id} lacks source tag")
            return False
        
        # 规则2: 检查是否是Seed数据
        invalid_tags = ['Derby', 'Big6', '惨败', 'Title Race', '关键战', '__SEED_DATA__']
        if any(tag in match.tags for tag in invalid_tags):
            logger.warning(f"Match {match.match_id} is seed/test data")
            return False
        
        # 规则3: 检查日期合理性
        if match.status == "FINISHED":
            if match.match_date > datetime.now(timezone.utc):
                logger.warning(f"Match {match.match_id} has future date but FINISHED status")
                return False
        
        return True
```

#### 6. 环境隔离

```yaml
# config/db.yaml
environments:
  production:
    database_url: postgresql+asyncpg://prod_user:***@prod-db:5432/sport_agent
    allow_seed_data: false  # ✅ 生产环境禁止Seed数据
  
  development:
    database_url: postgresql+asyncpg://dev_user:***@localhost:5432/sport_agent_dev
    allow_seed_data: true
  
  testing:
    database_url: postgresql+asyncpg://test_user:***@localhost:5432/sport_agent_test
    allow_seed_data: true
```

### 长期优化 (Medium Priority)

#### 7. 实施数据血缘追踪 (Data Lineage)

在 `Match` 模型中增加字段:

```python
class Match(Base):
    # ... 现有字段 ...
    
    # 数据血缘字段
    data_source: str = Column(String, nullable=False)  # "football-data.org", "api-football", etc.
    data_source_id: str = Column(String, nullable=True)  # 外部系统的原始ID
    ingestion_timestamp: datetime = Column(DateTime, nullable=False)  # 摄取时间
    last_verified_at: datetime = Column(DateTime, nullable=True)  # 最后验证时间
    is_verified: bool = Column(Boolean, default=False)  # 是否已人工验证
```

#### 8. 自动化数据质量监控

```python
async def run_data_quality_checks():
    """定期运行数据质量检查"""
    
    checks = [
        check_duplicate_matches(),
        check_conflicting_results(),
        check_seed_data_contamination(),  # ✅ 新增
        check_missing_source_tags(),      # ✅ 新增
        check_temporal_anomalies(),
    ]
    
    results = await asyncio.gather(*checks)
    
    if any(not result.passed for result in results):
        send_alert_to_admin(results)
```

---

## 📋 执行清单

### 立即执行 (今天)

- [ ] 1. 运行数据清理脚本，删除虚假Seed数据
- [ ] 2. 禁用 `scripts/seed_db.py`
- [ ] 3. 修改 `match_tool.py`，过滤非API数据
- [ ] 4. 重新运行测试，验证Agent输出的真实性

### 本周内

- [ ] 5. 实施数据标签规范
- [ ] 6. 添加数据验证中间件
- [ ] 7. 配置环境隔离（dev/test/prod）
- [ ] 8. 更新测试脚本，使用独立测试数据库

### 下个Sprint

- [ ] 9. 增加数据血缘追踪字段
- [ ] 10. 实施自动化数据质量监控
- [ ] 11. 编写数据真实性验证的单元测试
- [ ] 12. 更新运维文档和SOP

---

## 🎯 预期结果

完成上述改进后:

### Before ❌
```
用户: 曼联最近5场比赛的战绩如何？

Agent: 
- 2025-11-24: 曼联 vs 埃弗顿 (0:1) (负)
- 2025-11-21: 曼联 vs 利物浦 (0:3) (负) ⚠️ 虚假数据
- ...
```

### After ✅
```
用户: 曼联最近5场比赛的战绩如何？

Agent:
- 2025-11-24: 曼联 vs 埃弗顿 (0:1) (负) ✅ 真实
- 2025-11-08: 托特纳姆热刺 vs 曼联 (2:2) (平) ✅ 真实
- 2025-11-01: 诺丁汉森林 vs 曼联 (2:2) (平) ✅ 真实
- 2025-10-25: 曼联 vs 布莱顿 (4:2) (胜) ✅ 真实
- 2025-10-18: 曼联 vs 狼队 (1-0) (胜) ✅ 真实

数据来源: football-data.org API (已验证)
```

---

## 📚 参考资料

1. **Football-data.org API文档**: https://www.football-data.org/documentation/quickstart
2. **数据质量维度**: Completeness, Accuracy, Consistency, Timeliness, Validity, Uniqueness
3. **数据血缘追踪最佳实践**: https://www.datacouncil.ai/talks/data-lineage-best-practices

---

**报告生成时间**: 2025-11-25  
**审查人员**: AI Backend Engineer  
**下次审查日期**: 2025-12-02

