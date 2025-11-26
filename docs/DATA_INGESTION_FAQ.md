# 数据摄取常见问题解答 (FAQ)

## Q1: 多次运行数据摄取会造成数据冗余吗？

**答案：不会！** ✅

系统使用 **UPSERT 机制**（PostgreSQL 的 `ON CONFLICT DO UPDATE`）：

```python
# src/data_pipeline/ingest_football_data_v2.py:324-335
stmt = insert(Match).values(match_data)
stmt = stmt.on_conflict_do_update(
    index_elements=['match_id'],  # 以 match_id 为唯一键
    set_={
        "status": stmt.excluded.status,
        "home_score": stmt.excluded.home_score,
        "away_score": stmt.excluded.away_score,
        "result": stmt.excluded.result,
        "updated_at": func.now()
    }
)
```

**工作原理：**
- 如果 `match_id` 已存在 → **更新**比分、状态等信息
- 如果 `match_id` 不存在 → **插入**新记录

**结论：** 可以**安全地多次运行**数据摄取脚本，只会更新最新数据（如实时比分更新）。

---

## Q2: 出现"无法解析球队名称"警告怎么办？

### 警告示例

```
WARNING - 无法解析球队名称: 'Brentford FC' (来源: football-data.org), 最佳匹配: GEN (相似度: 57.14%)
WARNING - 无法解析球队名称: 'FC Bayern München' (来源: football-data.org), 最佳匹配: BOU (相似度: 50.00%)
```

### 原因分析

`EntityResolver` 使用 **85% 相似度阈值**进行模糊匹配：
- Football-data.org API 返回 "Brentford FC"
- 数据库中存储为 "Brentford" 或 "Brentford (布伦特福德)"
- 相似度低于 85% → 匹配失败

### 解决方案

**方法 1：运行批量修复脚本（推荐）⭐**

```bash
source .venv/bin/activate
python scripts/batch_fix_all_aliases.py
```

这会：
1. ✅ 更新所有主流联赛球队的标准名称
2. ✅ 添加 API 使用的完整名称（如 "Brentford FC"）
3. ✅ 保留中文别名（用户友好）
4. ✅ 处理冲突的 team_id（如 BRE 在英超和法甲）

**方法 2：使用别名管理工具**

```bash
python scripts/manage_team_aliases.py
```

选择选项：
- **3** - 批量添加主要球队中文别名
- **5** - 导出到 CSV 进行手动编辑
- **6** - 从 CSV 导入更新

**方法 3：降低匹配阈值（不推荐）**

修改 `src/data_pipeline/entity_resolver.py:172`:

```python
fuzzy_threshold: float = 0.60  # 从 0.85 降至 0.60
```

⚠️ **风险**：可能导致错误匹配。

---

## Q3: 为什么警告后数据还是成功入库了？

### 自动创建机制

当 `EntityResolver` 无法解析时，系统会**自动创建新球队**：

```python
# src/data_pipeline/ingest_football_data_v2.py:268-270
if not home_id:
    home_id = await self._create_team(
        db, ext_match.homeTeam.name, ext_match.homeTeam.tla, league_id
    )
    await db.commit()
    await entity_resolver.initialize()  # 重新加载缓存
```

日志输出：

```
创建或确认球队: Brentford FC -> BRE
```

### 潜在问题

虽然数据成功入库，但可能导致：
1. **重复球队**：同一球队因名称不同被创建多次
2. **查询不一致**：用户查询"拜仁"可能找不到"FC Bayern München"的数据

### 最佳实践

✅ 定期运行 `batch_fix_all_aliases.py` 维护球队别名映射

---

## Q4: 如何验证数据摄取是否正常？

### 方法 1：使用快速验证脚本

```bash
python scripts/quick_verify_data.py
```

会显示：
- 各联赛比赛数量统计
- 最近的比赛记录
- 数据完整性检查

### 方法 2：使用数据库状态检查工具

```bash
python scripts/check_database_status.py
```

显示：
- 所有联赛统计
- 球队统计（包括中文别名覆盖率）
- 最近比赛
- 数据质量报告

### 方法 3：SQL 查询

```sql
-- 查看各联赛比赛数
SELECT league_id, COUNT(*) as match_count
FROM matches
GROUP BY league_id
ORDER BY league_id;

-- 查看最近的比赛
SELECT 
    m.match_id,
    l.league_name,
    ht.team_name as home_team,
    at.team_name as away_team,
    m.home_score,
    m.away_score,
    m.status,
    m.match_date
FROM matches m
JOIN leagues l ON m.league_id = l.league_id
JOIN teams ht ON m.home_team_id = ht.team_id
JOIN teams at ON m.away_team_id = at.team_id
ORDER BY m.match_date DESC
LIMIT 20;
```

---

## Q5: 增量更新 vs 全量更新有什么区别？

### 增量更新（默认）

```bash
python src/data_pipeline/ingest_football_data_v2.py
```

- **时间范围**：回溯 90 天 + 未来 30 天
- **适用场景**：日常数据更新
- **优点**：速度快，API 调用少
- **日志**：`增量更新模式: 2025-08-28 到 2025-12-26`

### 全量更新

修改 `ingest_football_data_v2.py` 中的 `incremental=False`：

```python
# 第 452 行
await ingestor.ingest_league(
    league_code, 
    incremental=False  # 改为 False
)
```

- **时间范围**：整个赛季
- **适用场景**：初次部署、数据重建
- **缺点**：慢，API 调用多

---

## Q6: EntityResolver 的工作原理是什么？

### 多策略匹配

`EntityResolver` 使用 3 层匹配策略：

```python
# src/data_pipeline/entity_resolver.py:168-220

# 策略 1: 精确匹配
if external_lower in self._team_cache:
    return self._team_cache[external_lower]

# 策略 2: 去除后缀匹配
cleaned_name = external_name.replace(" FC", "").replace(" CF", "")
if cleaned_name in self._team_cache:
    return self._team_cache[cleaned_name]

# 策略 3: 模糊匹配（SequenceMatcher，阈值 85%）
score = SequenceMatcher(None, external_lower, cached_name).ratio()
if score >= fuzzy_threshold:
    return team_id
```

### 自动生成别名

从球队名称自动提取多种别名：

```python
"Manchester United (曼联)" →
  - "Manchester United"
  - "曼联"
  - "Manchester"  # 去除 "United" 后缀
  - "MUN"  # team_id 本身
```

### 缓存机制

```python
self._team_cache: Dict[str, str] = {}  # 别名 -> team_id
self._team_info: Dict[str, Dict] = {}  # team_id -> 完整信息
```

初始化时从数据库加载所有球队，构建别名缓存。

---

## Q7: 如何添加新的球队别名？

### 方法 1：更新批量修复脚本（推荐）

编辑 `scripts/batch_fix_all_aliases.py`，添加到 `COMPREHENSIVE_TEAM_ALIASES`：

```python
COMPREHENSIVE_TEAM_ALIASES = {
    # ... 现有映射 ...
    
    # 新增球队
    "NEW_ID": "Full Team Name (中文名)",
}
```

### 方法 2：直接更新数据库

```sql
UPDATE teams 
SET team_name = 'Full Team Name (中文名)' 
WHERE team_id = 'TEAM_ID';
```

### 方法 3：使用管理工具

```bash
python scripts/manage_team_aliases.py
# 选择 5 导出 CSV → 编辑 → 选择 6 导入
```

---

## Q8: 数据摄取的最佳实践流程是什么？

### 初次部署

```bash
# 1. 初始化数据库
alembic upgrade head

# 2. 种子联赛数据
python scripts/seed_leagues.py

# 3. 修复球队别名
python scripts/batch_fix_all_aliases.py

# 4. 全量数据摄取（修改 incremental=False）
python src/data_pipeline/ingest_football_data_v2.py

# 5. 验证数据
python scripts/quick_verify_data.py
```

### 日常维护

```bash
# 每日增量更新（可设置 cron job）
python src/data_pipeline/ingest_football_data_v2.py

# 每周验证数据质量
python scripts/check_database_status.py
```

### 问题排查

```bash
# 1. 检查数据库状态
python scripts/check_database_status.py

# 2. 如果有别名警告
python scripts/batch_fix_all_aliases.py

# 3. 重新摄取数据
python src/data_pipeline/ingest_football_data_v2.py
```

---

## Q9: API 限额和速率限制如何处理？

### Football-data.org 限制

- **免费版**：10 次/分钟，无并发
- **付费版**：更高限额

### 当前实现

```python
# src/data_pipeline/ingest_football_data_v2.py:95-99
headers = {
    "X-Auth-Token": self.api_key
}

# 每个联赛之间有 3 秒延迟（第 241-252 行）
await asyncio.sleep(3)
```

### 优化建议

1. **使用付费 API**（生产环境推荐）
2. **添加指数退避重试**
3. **使用 Redis 缓存**减少 API 调用

---

## Q10: 如何监控数据质量？

### 内置数据质量检查

```python
# src/data_pipeline/ingest_football_data_v2.py:182-206
async def _validate_match_data(self, match_data: dict) -> bool:
    # 1. 必填字段检查
    # 2. 比分非负检查
    # 3. 主客队不能相同
    # 4. 日期合理性检查
```

### 质量监控指标

运行数据摄取后查看统计：

```
============================================================
数据摄取任务完成！统计信息：
  - 总获取: 808 场
  - 成功入库: 808 场
  - 实体解析失败: 0 场
  - 错误: 0 场
  - 耗时: 30.45 秒
============================================================
```

### 告警阈值

建议设置：
- ⚠️ 实体解析失败率 > 5%
- ⚠️ 错误率 > 1%
- ⚠️ 耗时 > 60 秒（可能网络问题）

---

## 相关文件

- `src/data_pipeline/ingest_football_data_v2.py` - 数据摄取主脚本
- `src/data_pipeline/entity_resolver.py` - 实体解析核心
- `scripts/batch_fix_all_aliases.py` - 批量别名修复
- `scripts/manage_team_aliases.py` - 别名管理工具
- `scripts/check_database_status.py` - 数据库状态检查
- `scripts/quick_verify_data.py` - 快速验证

---

## 总结

✅ **重复运行安全**：UPSERT 机制保证不会重复
✅ **自动创建球队**：无法匹配时自动创建
✅ **别名可维护**：多种工具支持别名管理
✅ **数据质量保证**：多层验证和监控

**推荐工作流程：**
1. 定期运行 `ingest_football_data_v2.py`（增量更新）
2. 每周运行 `batch_fix_all_aliases.py`（维护别名）
3. 定期运行 `check_database_status.py`（质量监控）

