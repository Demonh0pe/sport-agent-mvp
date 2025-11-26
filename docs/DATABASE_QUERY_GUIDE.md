# 数据库查询指南

## 📚 目录
1. [快速开始](#快速开始)
2. [常用命令](#常用命令)
3. [使用psql命令行](#使用psql命令行)
4. [使用Python脚本](#使用python脚本)
5. [常见SQL查询](#常见sql查询)

---

## 🚀 快速开始

### 方法1: 使用我们的脚本（推荐）

```bash
# 查看数据摘要（默认）
python scripts/check_database_status.py

# 查看所有信息
python scripts/check_database_status.py --all

# 查看特定内容
python scripts/check_database_status.py --teams       # 所有球队
python scripts/check_database_status.py --leagues     # 所有联赛
python scripts/check_database_status.py --matches     # 最近比赛
python scripts/check_database_status.py --standings   # 积分榜

# 查看特定表的详细信息
python scripts/check_database_status.py --table leagues
python scripts/check_database_status.py --table teams
python scripts/check_database_status.py --table matches
python scripts/check_database_status.py --table standings
```

---

## 💡 常用命令

### 1. 查看数据摘要
```bash
python scripts/check_database_status.py
```
显示：
- 各表记录数
- 比赛统计（按状态、联赛）
- 数据质量检查

### 2. 查看所有球队
```bash
python scripts/check_database_status.py --teams
```

按联赛分组显示所有球队：
```
【EPL】
  - Manchester United (MUN)
  - Liverpool (LIV)
  - Arsenal (ARS)
  ...

【BL1】
  - Bayern München (FCB)
  - Borussia Dortmund (BVB)
  ...
```

### 3. 查看最近比赛
```bash
# 默认显示20场
python scripts/check_database_status.py --matches

# 显示50场
python scripts/check_database_status.py --matches --limit 50
```

### 4. 查看积分榜
```bash
# 所有联赛前10名
python scripts/check_database_status.py --standings

# 指定联赛
python scripts/check_database_status.py --standings --league EPL
```

### 5. 查看指定联赛的球队
```bash
python scripts/check_database_status.py --teams --league EPL
```

---

## 🖥️ 使用psql命令行

### 连接数据库
```bash
# 使用配置文件中的信息
psql -h localhost -p 5432 -U sport_agent -d sport_agent
# 密码: changeme
```

### 常用psql命令
```sql
-- 列出所有表
\dt

-- 查看表结构
\d leagues
\d teams
\d matches
\d standings

-- 查看表记录数
SELECT COUNT(*) FROM leagues;
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM matches;
SELECT COUNT(*) FROM standings;

-- 退出
\q
```

---

## 🐍 使用Python脚本

### 创建自定义查询脚本

```python
import asyncio
from sqlalchemy import select
from src.infra.db.session import AsyncSessionLocal
from src.infra.db.models import Team, Match

async def my_query():
    async with AsyncSessionLocal() as db:
        # 查询所有英超球队
        stmt = select(Team).where(Team.league_id == "EPL")
        result = await db.execute(stmt)
        teams = result.scalars().all()
        
        for team in teams:
            print(f"{team.team_name} ({team.team_id})")

asyncio.run(my_query())
```

---

## 📝 常见SQL查询

### 1. 查看联赛信息
```sql
-- 所有联赛
SELECT league_id, league_name, country, season 
FROM leagues 
ORDER BY league_name;

-- 特定联赛
SELECT * FROM leagues WHERE league_id = 'EPL';
```

### 2. 查看球队信息
```sql
-- 所有球队
SELECT team_id, team_name, league_id 
FROM teams 
ORDER BY league_id, team_name;

-- 英超球队
SELECT team_name FROM teams WHERE league_id = 'EPL';

-- 统计每个联赛的球队数
SELECT league_id, COUNT(*) as team_count 
FROM teams 
GROUP BY league_id;
```

### 3. 查看比赛信息
```sql
-- 最近10场已完成的比赛
SELECT 
    match_datetime,
    home_team_name,
    home_score,
    away_score,
    away_team_name,
    status
FROM matches 
WHERE status = 'FINISHED'
ORDER BY match_datetime DESC 
LIMIT 10;

-- 统计各状态的比赛数
SELECT status, COUNT(*) 
FROM matches 
GROUP BY status;

-- 某支球队的所有比赛
SELECT 
    match_datetime,
    home_team_name,
    home_score,
    away_score,
    away_team_name
FROM matches 
WHERE home_team_name = 'Manchester United' 
   OR away_team_name = 'Manchester United'
ORDER BY match_datetime DESC;

-- 高分比赛（总进球>=5）
SELECT 
    match_datetime,
    home_team_name,
    home_score,
    away_score,
    away_team_name,
    (home_score + away_score) as total_goals
FROM matches 
WHERE status = 'FINISHED'
  AND home_score IS NOT NULL
  AND away_score IS NOT NULL
  AND (home_score + away_score) >= 5
ORDER BY total_goals DESC;
```

### 4. 查看积分榜
```sql
-- 英超积分榜前10
SELECT 
    position,
    t.team_name,
    played_games,
    won,
    draw,
    lost,
    goals_for,
    goals_against,
    goal_difference,
    points
FROM standings s
JOIN teams t ON s.team_id = t.team_id
WHERE s.league_id = 'EPL' AND s.season = '2024'
ORDER BY position
LIMIT 10;

-- 查看球队在积分榜的位置
SELECT 
    position,
    played_games,
    won,
    draw,
    lost,
    points
FROM standings s
JOIN teams t ON s.team_id = t.team_id
WHERE t.team_name = 'Liverpool' AND s.season = '2024';
```

### 5. 统计查询
```sql
-- 各联赛的比赛数量
SELECT 
    league_id,
    COUNT(*) as match_count,
    SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) as finished,
    SUM(CASE WHEN status = 'SCHEDULED' THEN 1 ELSE 0 END) as scheduled
FROM matches 
GROUP BY league_id;

-- 主场优势分析
SELECT 
    league_id,
    COUNT(*) as total_matches,
    SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as home_wins,
    SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) as away_wins,
    SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) as draws,
    ROUND(100.0 * SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) / COUNT(*), 2) as home_win_rate
FROM matches 
WHERE status = 'FINISHED' 
  AND home_score IS NOT NULL 
  AND away_score IS NOT NULL
GROUP BY league_id;

-- 进球最多的球队（作为主队）
SELECT 
    home_team_name,
    COUNT(*) as matches,
    SUM(home_score) as total_goals,
    ROUND(AVG(home_score::numeric), 2) as avg_goals_per_match
FROM matches 
WHERE status = 'FINISHED' AND home_score IS NOT NULL
GROUP BY home_team_name
ORDER BY total_goals DESC
LIMIT 10;
```

### 6. 复杂分析查询
```sql
-- 球队近期表现（最近5场）
WITH recent_matches AS (
    SELECT 
        match_id,
        match_datetime,
        CASE 
            WHEN home_team_name = 'Manchester United' THEN home_team_name
            ELSE away_team_name
        END as team,
        CASE 
            WHEN home_team_name = 'Manchester United' AND home_score > away_score THEN 'W'
            WHEN away_team_name = 'Manchester United' AND away_score > home_score THEN 'W'
            WHEN home_score = away_score THEN 'D'
            ELSE 'L'
        END as result
    FROM matches 
    WHERE (home_team_name = 'Manchester United' OR away_team_name = 'Manchester United')
      AND status = 'FINISHED'
    ORDER BY match_datetime DESC
    LIMIT 5
)
SELECT 
    team,
    COUNT(*) as matches,
    SUM(CASE WHEN result = 'W' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
    SUM(CASE WHEN result = 'L' THEN 1 ELSE 0 END) as losses
FROM recent_matches
GROUP BY team;

-- 直接对抗记录
SELECT 
    match_datetime,
    home_team_name,
    home_score,
    away_score,
    away_team_name,
    CASE 
        WHEN home_score > away_score THEN home_team_name
        WHEN away_score > home_score THEN away_team_name
        ELSE 'Draw'
    END as winner
FROM matches 
WHERE ((home_team_name = 'Manchester United' AND away_team_name = 'Liverpool')
   OR (home_team_name = 'Liverpool' AND away_team_name = 'Manchester United'))
  AND status = 'FINISHED'
ORDER BY match_datetime DESC;
```

---

## 🔧 数据质量检查

### 检查缺失数据
```sql
-- 已完成但没有比分的比赛
SELECT COUNT(*) 
FROM matches 
WHERE status = 'FINISHED' 
  AND (home_score IS NULL OR away_score IS NULL);

-- 没有比赛记录的球队
SELECT t.team_name 
FROM teams t
WHERE NOT EXISTS (
    SELECT 1 FROM matches m 
    WHERE m.home_team_id = t.team_id 
       OR m.away_team_id = t.team_id
);

-- 积分榜覆盖情况
SELECT 
    l.league_id,
    l.league_name,
    CASE WHEN s.league_id IS NOT NULL THEN '有' ELSE '无' END as has_standings
FROM leagues l
LEFT JOIN (
    SELECT DISTINCT league_id FROM standings
) s ON l.league_id = s.league_id;
```

---

## 📊 可视化查询（适合导出到Excel）

### 导出联赛摘要
```sql
SELECT 
    l.league_name as "联赛",
    l.country as "国家",
    COUNT(DISTINCT t.team_id) as "球队数",
    COUNT(m.match_id) as "比赛数",
    SUM(CASE WHEN m.status = 'FINISHED' THEN 1 ELSE 0 END) as "已完成",
    SUM(CASE WHEN m.status = 'SCHEDULED' THEN 1 ELSE 0 END) as "未开始"
FROM leagues l
LEFT JOIN teams t ON l.league_id = t.league_id
LEFT JOIN matches m ON l.league_id = m.league_id
GROUP BY l.league_id, l.league_name, l.country
ORDER BY "比赛数" DESC;
```

---

## 🛠️ 高级技巧

### 1. 使用psql输出到文件
```bash
psql -h localhost -p 5432 -U sport_agent -d sport_agent \
  -c "SELECT * FROM teams WHERE league_id = 'EPL';" \
  -o teams_epl.txt
```

### 2. 执行SQL文件
```bash
psql -h localhost -p 5432 -U sport_agent -d sport_agent \
  -f my_query.sql
```

### 3. 格式化输出
```sql
-- 在psql中
\x  -- 开启扩展显示（每行一个字段）
SELECT * FROM teams LIMIT 1;
\x  -- 关闭扩展显示
```

---

## 🆘 故障排查

### 连接问题
```bash
# 检查PostgreSQL是否运行
pg_isready -h localhost -p 5432

# 测试连接
psql -h localhost -p 5432 -U sport_agent -d sport_agent -c "SELECT 1;"
```

### 权限问题
```sql
-- 检查当前用户权限
SELECT current_user;
\du

-- 检查表权限
\dp
```

### 性能问题
```sql
-- 查看慢查询
SELECT * FROM pg_stat_activity WHERE state != 'idle';

-- 查看表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 📚 相关资源

- [PostgreSQL官方文档](https://www.postgresql.org/docs/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [项目数据库模型](../src/infra/db/models.py)
- [数据库迁移](../migrations/)

---

## ✅ 快速检查清单

在数据导入后，使用以下命令验证：

```bash
# 1. 检查数据摘要
python scripts/check_database_status.py

# 2. 验证每个联赛都有数据
python scripts/check_database_status.py --leagues

# 3. 检查球队列表
python scripts/check_database_status.py --teams

# 4. 查看最新比赛
python scripts/check_database_status.py --matches --limit 10

# 5. 验证积分榜
python scripts/check_database_status.py --standings

# 6. 完整检查
python scripts/check_database_status.py --all
```

---

**提示**: 将常用查询保存为shell脚本或SQL文件，方便日常使用！

