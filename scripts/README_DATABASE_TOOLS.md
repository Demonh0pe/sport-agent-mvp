# 数据库查询工具 - 快速参考

## 🚀 快速开始

```bash
# 1. 查看数据摘要（最常用）
python scripts/check_database_status.py

# 2. 查看所有详细信息
python scripts/check_database_status.py --all
```

---

## 📋 常用命令

### 基础查询

```bash
# 数据摘要（表统计 + 比赛统计 + 数据质量）
python scripts/check_database_status.py

# 输出示例:
# ✅ 数据库连接成功
# 📌 PostgreSQL版本: PostgreSQL 15.15
#
# 📊 数据库表统计
#   联赛 (leagues)              6 条记录
#   球队 (teams)              120 条记录
#   比赛 (matches)            808 条记录
#   积分榜 (standings)         96 条记录
```

### 查看联赛

```bash
python scripts/check_database_status.py --leagues

# 输出:
#   📌 Premier League (英超)
#      ID: EPL
#      国家: England
#      级别: 1
#
#   📌 德国甲级联赛
#      ID: BL1
#      国家: Germany
#      级别: 1
```

### 查看球队

```bash
# 所有球队
python scripts/check_database_status.py --teams

# 指定联赛的球队
python scripts/check_database_status.py --teams --league EPL
python scripts/check_database_status.py --teams --league BL1
```

### 查看比赛

```bash
# 最近20场比赛（默认）
python scripts/check_database_status.py --matches

# 最近50场比赛
python scripts/check_database_status.py --matches --limit 50

# 最近10场比赛
python scripts/check_database_status.py --matches --limit 10
```

### 查看积分榜

```bash
# 所有联赛前10名（默认）
python scripts/check_database_status.py --standings

# 前20名
python scripts/check_database_status.py --standings --limit 20

# 指定联赛
python scripts/check_database_status.py --standings --league EPL
python scripts/check_database_status.py --standings --league BL1
python scripts/check_database_status.py --standings --league PD
```

### 查看表详情

```bash
python scripts/check_database_status.py --table leagues
python scripts/check_database_status.py --table teams
python scripts/check_database_status.py --table matches
python scripts/check_database_status.py --table standings
```

---

## 🔥 组合查询

```bash
# 查看联赛 + 球队 + 最近比赛
python scripts/check_database_status.py --leagues --teams --matches --limit 10

# 查看英超完整信息
python scripts/check_database_status.py --teams --matches --standings --league EPL

# 查看所有信息（非常详细）
python scripts/check_database_status.py --all
```

---

## 💡 实际使用场景

### 场景1: 每日数据检查
```bash
# 快速检查数据是否正常
python scripts/check_database_status.py

# 查看输出中的关键指标:
# - 各表记录数是否正常
# - 已完成/未开始比赛数量
# - 数据质量警告
```

### 场景2: 数据导入后验证
```bash
# 1. 先看摘要
python scripts/check_database_status.py

# 2. 检查新导入的联赛
python scripts/check_database_status.py --teams --league BL1

# 3. 验证积分榜
python scripts/check_database_status.py --standings --league BL1

# 4. 查看最新比赛
python scripts/check_database_status.py --matches --limit 20
```

### 场景3: 调试问题
```bash
# 问题: "为什么找不到某个球队?"
python scripts/check_database_status.py --teams --league EPL | grep "Liverpool"

# 问题: "最近的比赛数据正常吗?"
python scripts/check_database_status.py --matches --limit 10

# 问题: "有多少积分榜数据?"
python scripts/check_database_status.py | grep "积分榜"

# 问题: "数据质量如何?"
python scripts/check_database_status.py | grep -A 10 "数据质量"
```

---

## 📊 输出示例

### 数据摘要
```
================================================================================
📊 数据库表统计
================================================================================
  联赛 (leagues)                            6 条记录
  球队 (teams)                            120 条记录
  比赛 (matches)                          808 条记录
  积分榜 (standings)                        96 条记录
================================================================================

================================================================================
📈 比赛统计
================================================================================

  比赛状态分布:
    🔄 FIXTURE            227 场
    ✅ FINISHED           581 场

  联赛比赛数量:
    📌 EPL                150 场
    📌 FL1                126 场
    📌 SA                 146 场
    📌 UCL                108 场
    📌 BL1                126 场
    📌 PD                 152 场

  比赛时间范围:
    最早: 2025-08-27
    最晚: 2025-12-22
================================================================================

================================================================================
🔍 数据质量检查
================================================================================

  ⚠️  没有比赛记录的球队: 13
  ⚠️  已完成但缺少比分的比赛: 0
  ✅ 有积分榜的联赛: 5/6
================================================================================
```

### 积分榜
```
================================================================================
📊 积分榜
================================================================================

  排名     球队                        赛    胜    平    负    进     失     净胜     积分    
  --------------------------------------------------------------------------------

  【BL1】
  1      FC Barcelona              34   25   7    2    99    32       +67 82    
  2      Bayer 04 Leverkusen       34   19   12   3    72    43       +29 69    
  3      Eintracht Frankfurt       34   17   9    8    68    46       +22 60    
  ...
```

---

## 🛠️ 使用psql直接查询

如果您想使用SQL，可以直接连接PostgreSQL：

```bash
# 连接数据库
psql -h localhost -p 5432 -U sport_agent -d sport_agent
# 密码: changeme
```

常用SQL查询：

```sql
-- 查看所有表
\dt

-- 查看联赛
SELECT * FROM leagues;

-- 查看英超球队
SELECT team_name FROM teams WHERE league_id = 'EPL';

-- 查看最近10场已完成的比赛
SELECT 
    match_date,
    home_team_id,
    home_score,
    away_score,
    away_team_id
FROM matches 
WHERE status = 'FINISHED'
ORDER BY match_date DESC 
LIMIT 10;

-- 查看英超积分榜
SELECT 
    position,
    t.team_name,
    points,
    won,
    draw,
    lost
FROM standings s
JOIN teams t ON s.team_id = t.team_id
WHERE s.league_id = 'EPL'
ORDER BY position
LIMIT 10;
```

---

## 📖 完整文档

详细的查询指南和SQL示例，请参考:
- [DATABASE_QUERY_GUIDE.md](../docs/DATABASE_QUERY_GUIDE.md)

---

## 💡 提示

1. **管道处理**: 所有命令输出都可以通过管道处理
   ```bash
   python scripts/check_database_status.py --teams | grep "Manchester"
   ```

2. **保存输出**: 将结果保存到文件
   ```bash
   python scripts/check_database_status.py --all > database_report.txt
   ```

3. **定期检查**: 建议每天运行一次数据摘要检查
   ```bash
   python scripts/check_database_status.py
   ```

4. **数据导入后**: 务必运行全面检查
   ```bash
   python scripts/check_database_status.py --all
   ```

---

## 🆘 遇到问题？

### 连接失败
```bash
# 检查PostgreSQL是否运行
docker ps | grep postgres

# 或
pg_isready -h localhost -p 5432
```

### 数据不对
```bash
# 查看数据质量检查
python scripts/check_database_status.py | grep -A 10 "数据质量"
```

### 需要更多信息
```bash
# 查看详细指南
cat docs/DATABASE_QUERY_GUIDE.md
```

