# 球队别名解析问题修复指南

## 问题描述

在运行 `ingest_football_data_v2.py` 时出现警告：

```
WARNING - 无法解析球队名称: 'FC Barcelona' (来源: football-data.org), 最佳匹配: FCB (相似度: 62.07%)
WARNING - 无法解析球队名称: 'Stade Brestois 29' (来源: football-data.org), 最佳匹配: REN (相似度: 63.16%)
WARNING - 无法解析球队名称: 'AFC Ajax' (来源: football-data.org), 最佳匹配: FCA (相似度: 54.55%)
```

## 根本原因

`EntityResolver` 使用 **85% 相似度阈值** 进行模糊匹配，但：
- Football-data.org API 返回的球队名称（如 "FC Barcelona"）
- 与数据库中的球队名称（如 "Barcelona (巴塞罗那)"）相似度低于 85%
- 导致无法自动匹配

## 解决方案

### 方法 1：运行自动修复脚本（推荐）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行修复脚本
python scripts/fix_missing_aliases.py
```

**脚本会自动：**
1. 检查数据库中的球队状态
2. 更新球队名称，添加外部API使用的名称
3. 验证修复是否成功

**更新内容：**
- `FCB`: → `FC Barcelona (巴塞罗那)`
- `BRE`: → `Stade Brestois 29 (布雷斯特)`
- `AJA`: → `AFC Ajax (阿贾克斯)`

### 方法 2：手动SQL更新（适合熟悉数据库的用户）

```bash
# 连接到PostgreSQL
psql -h localhost -U sport_agent -d sport_agent_db

# 执行更新
\i scripts/fix_team_aliases.sql
```

或者直接执行SQL：

```sql
UPDATE teams SET team_name = 'FC Barcelona (巴塞罗那)' WHERE team_id = 'FCB';
UPDATE teams SET team_name = 'Stade Brestois 29 (布雷斯特)' WHERE team_id = 'BRE';
UPDATE teams SET team_name = 'AFC Ajax (阿贾克斯)' WHERE team_id = 'AJA';
```

### 方法 3：调整匹配阈值（不推荐）

修改 `src/data_pipeline/entity_resolver.py`:

```python
async def resolve_team(
    self, 
    external_name: str,
    source: str = "football-data.org",
    fuzzy_threshold: float = 0.60  # 从 0.85 降至 0.60
) -> Optional[str]:
```

**风险：** 可能导致错误匹配（如 FCB 匹配到 FCA）

## 验证修复

修复后重新运行数据摄取：

```bash
python src/data_pipeline/ingest_football_data_v2.py
```

应该不再出现上述警告。

## 预防措施

### 添加更多球队别名

使用 `manage_team_aliases.py` 工具批量管理别名：

```bash
python scripts/manage_team_aliases.py
```

选择：
- **选项 3**：批量添加主要球队中文别名
- **选项 5**：导出球队数据到CSV进行手动编辑
- **选项 6**：从CSV导入更新后的别名

### EntityResolver 工作原理

`EntityResolver` 使用多策略匹配：

1. **精确匹配**：直接匹配球队名称或ID
2. **别名匹配**：匹配自动生成的别名（去除前后缀）
3. **模糊匹配**：使用 SequenceMatcher 计算相似度

**自动生成的别名包括：**
- 官方全名
- 中文名（括号内）
- 去除后缀（FC, CF, AFC, United, City等）
- 去除前缀（FC, CF, AFC, 1., TSG等）
- team_id 本身

示例：
```python
"Manchester United (曼联)" → ["Manchester United", "曼联", "Manchester", "MUN"]
"FC Barcelona" → ["FC Barcelona", "Barcelona", "FCB"]
```

## 常见问题

**Q: 为什么数据最终还是成功入库了？**

A: 当无法解析时，系统会使用最佳匹配或创建新球队记录。警告表明可能存在数据不一致的风险。

**Q: 这会影响后续查询吗？**

A: 可能会。如果球队名称不一致，用户查询"巴萨"时可能找不到"FC Barcelona"的比赛数据。

**Q: 需要重新摄取数据吗？**

A: 不需要。修复别名后，已入库的数据仍然有效。新的摄取会使用更新后的别名。

## 技术细节

### EntityResolver 缓存机制

```python
self._team_cache: Dict[str, str] = {}  # 别名 -> team_id
self._team_info: Dict[str, Dict] = {}  # team_id -> 完整信息
```

修复后需要重新初始化：

```python
entity_resolver._initialized = False
await entity_resolver.initialize()
```

### 相似度计算

使用 Python 内置 `difflib.SequenceMatcher`:

```python
from difflib import SequenceMatcher

score = SequenceMatcher(None, "FC Barcelona", "barcelona").ratio()
# 返回: 0.62 (62%)
```

## 相关文件

- `src/data_pipeline/entity_resolver.py` - 实体解析核心逻辑
- `scripts/fix_missing_aliases.py` - 自动修复脚本
- `scripts/manage_team_aliases.py` - 别名管理工具
- `scripts/fix_team_aliases.sql` - SQL修复脚本

## 总结

 **推荐流程：**
1. 运行 `python scripts/fix_missing_aliases.py`
2. 验证修复成功
3. 重新运行数据摄取
4. 定期使用 `manage_team_aliases.py` 维护别名

这是一个**数据质量维护**问题，而非系统错误。定期维护球队别名映射可以提高数据一致性。

