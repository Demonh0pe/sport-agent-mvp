# 数据扩展计划

## 当前状态

### 已有数据
- ✅ 联赛 (Leagues): 6 个
- ✅ 球队 (Teams): 49 支
- ✅ 比赛 (Matches): 62 场
- ✅ 用户画像 (Users)
- ✅ 资讯 (News)

### 缺失数据
- ❌ 球员信息
- ❌ 球员统计
- ❌ 积分榜
- ❌ 射手榜
- ❌ 比赛详细统计（射门、传球、控球率等）
- ❌ 球队详细信息（教练、球场、市值等）

---

## 扩展方案

### Phase 1: 核心数据扩展 (P0)

#### 1.1 球员数据 (Player)

**数据库模型**:
```python
class Player(Base):
    __tablename__ = "players"
    
    player_id = Column(String, primary_key=True, index=True)
    player_name = Column(String, nullable=False)
    team_id = Column(String, ForeignKey("teams.team_id"))
    
    # 基础信息
    position = Column(String)  # GK, DF, MF, FW
    nationality = Column(String)
    date_of_birth = Column(DateTime)
    shirt_number = Column(Integer)
    
    # 市场信息
    market_value = Column(Integer)  # 单位：欧元
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**数据来源**: 
- football-data.org API: `/teams/{id}` (包含球员名单)
- Transfermarkt (市场价值 - 可选)

**优先级**: P0（预测模型需要球员数据）

---

#### 1.2 积分榜 (Standings)

**数据库模型**:
```python
class Standing(Base):
    __tablename__ = "standings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String, ForeignKey("leagues.league_id"), index=True)
    team_id = Column(String, ForeignKey("teams.team_id"), index=True)
    season = Column(String, index=True)  # e.g., "2024-2025"
    
    # 排名信息
    position = Column(Integer)
    played_games = Column(Integer)
    won = Column(Integer)
    draw = Column(Integer)
    lost = Column(Integer)
    
    # 进球数据
    goals_for = Column(Integer)
    goals_against = Column(Integer)
    goal_difference = Column(Integer)
    
    # 积分
    points = Column(Integer)
    
    # 主客场分解（可选）
    home_won = Column(Integer)
    home_draw = Column(Integer)
    home_lost = Column(Integer)
    away_won = Column(Integer)
    away_draw = Column(Integer)
    away_lost = Column(Integer)
    
    # 时间戳
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        # 确保每个联赛、赛季、球队组合唯一
        UniqueConstraint('league_id', 'team_id', 'season', name='uq_standing'),
    )
```

**数据来源**: 
- football-data.org API: `/competitions/{id}/standings`

**优先级**: P0（用户常问"积分榜"、"排名"）

---

#### 1.3 球员赛季统计 (PlayerSeasonStats)

**数据库模型**:
```python
class PlayerSeasonStats(Base):
    __tablename__ = "player_season_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey("players.player_id"), index=True)
    season = Column(String, index=True)  # e.g., "2024-2025"
    league_id = Column(String, ForeignKey("leagues.league_id"), index=True)
    
    # 出场数据
    appearances = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    starts = Column(Integer, default=0)
    
    # 进攻数据
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    
    # 防守数据（针对防守球员）
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    clearances = Column(Integer, default=0)
    
    # 纪律
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    
    # 守门员专属（如果是门将）
    clean_sheets = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    goals_conceded = Column(Integer, default=0)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('player_id', 'season', 'league_id', name='uq_player_season'),
    )
```

**数据来源**: 
- football-data.org API: `/competitions/{id}/scorers` (射手榜)
- SofaScore / WhoScored (更详细的统计 - 可选)

**优先级**: P1（用户可能问"哈兰德进了多少球"）

---

### Phase 2: 比赛详细数据扩展 (P1)

#### 2.1 比赛统计 (MatchStats)

**数据库模型**:
```python
class MatchStats(Base):
    __tablename__ = "match_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String, ForeignKey("matches.match_id"), unique=True, index=True)
    
    # 控球率
    home_possession = Column(Float)
    away_possession = Column(Float)
    
    # 射门数据
    home_shots_total = Column(Integer)
    away_shots_total = Column(Integer)
    home_shots_on_target = Column(Integer)
    away_shots_on_target = Column(Integer)
    
    # 传球数据
    home_passes = Column(Integer)
    away_passes = Column(Integer)
    home_pass_accuracy = Column(Float)
    away_pass_accuracy = Column(Float)
    
    # 防守数据
    home_tackles = Column(Integer)
    away_tackles = Column(Integer)
    home_fouls = Column(Integer)
    away_fouls = Column(Integer)
    
    # 角球、任意球
    home_corners = Column(Integer)
    away_corners = Column(Integer)
    home_freekicks = Column(Integer)
    away_freekicks = Column(Integer)
    
    # 纪律
    home_yellow_cards = Column(Integer)
    away_yellow_cards = Column(Integer)
    home_red_cards = Column(Integer)
    away_red_cards = Column(Integer)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**数据来源**: 
- football-data.org API: `/matches/{id}` (有限的统计数据)
- RapidAPI SofaScore / API-Football (更详细的数据 - 需付费)

**优先级**: P1（预测模型的重要特征）

---

#### 2.2 球员比赛表现 (PlayerMatchPerformance)

**数据库模型**:
```python
class PlayerMatchPerformance(Base):
    __tablename__ = "player_match_performances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String, ForeignKey("matches.match_id"), index=True)
    player_id = Column(String, ForeignKey("players.player_id"), index=True)
    team_id = Column(String, ForeignKey("teams.team_id"), index=True)
    
    # 出场信息
    started = Column(Boolean, default=False)
    minutes_played = Column(Integer, default=0)
    
    # 表现数据
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    passes_completed = Column(Integer, default=0)
    passes_attempted = Column(Integer, default=0)
    
    # 评分
    rating = Column(Float)  # 如 7.8 / 10
    
    # 纪律
    yellow_card = Column(Boolean, default=False)
    red_card = Column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint('match_id', 'player_id', name='uq_player_match'),
    )
```

**数据来源**: 
- SofaScore API (最完整)
- API-Football (备选)

**优先级**: P2（高级功能 - "某球员本场表现"）

---

### Phase 3: 高级数据扩展 (P2)

#### 3.1 球队详细信息扩展

**扩展 Team 模型**:
```python
class Team(Base):
    # ... 现有字段 ...
    
    # 新增字段
    coach_name = Column(String)  # 主教练
    stadium_name = Column(String)  # 主场
    stadium_capacity = Column(Integer)  # 球场容量
    founded_year = Column(Integer)  # 成立年份
    club_colors = Column(String)  # 队服颜色
    website = Column(String)  # 官网
    market_value = Column(Integer)  # 球队总市值
```

**数据来源**: 
- football-data.org API: `/teams/{id}`
- Transfermarkt (市值)

**优先级**: P2

---

#### 3.2 转会数据 (Transfers)

**数据库模型**:
```python
class Transfer(Base):
    __tablename__ = "transfers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey("players.player_id"), index=True)
    
    from_team_id = Column(String, ForeignKey("teams.team_id"))
    to_team_id = Column(String, ForeignKey("teams.team_id"))
    
    transfer_date = Column(DateTime(timezone=True))
    transfer_fee = Column(Integer)  # 单位：欧元
    transfer_type = Column(String)  # loan, permanent, free
    
    season = Column(String, index=True)
```

**数据来源**: 
- Transfermarkt API (需爬虫或付费API)

**优先级**: P3（冬窗、夏窗转会预测）

---

#### 3.3 伤病数据 (Injuries)

**数据库模型**:
```python
class Injury(Base):
    __tablename__ = "injuries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey("players.player_id"), index=True)
    
    injury_type = Column(String)  # hamstring, knee, ankle
    start_date = Column(DateTime(timezone=True))
    expected_return_date = Column(DateTime(timezone=True))
    actual_return_date = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(String)  # active, recovered
```

**数据来源**: 
- Transfermarkt
- 球队官方公告（需爬虫）

**优先级**: P3（阵容预测、投注建议）

---

## 实施计划

### Week 1: Phase 1 - 核心数据扩展

**Task 1: 球员数据摄取**
1. 创建 `Player` 模型
2. 添加 Alembic 迁移
3. 扩展 `ingest_football_data_v2.py`，添加球员抓取逻辑
4. 测试：查询"哈兰德个人信息"

**Task 2: 积分榜数据摄取**
1. 创建 `Standing` 模型
2. 添加 Alembic 迁移
3. 创建 `ingest_standings.py` 脚本
4. 测试：查询"英超积分榜"

**Task 3: 球员统计数据摄取**
1. 创建 `PlayerSeasonStats` 模型
2. 添加 Alembic 迁移
3. 创建 `ingest_scorers.py` 脚本（射手榜）
4. 测试：查询"哈兰德进了多少球"

### Week 2: Phase 2 - 比赛详细数据

**Task 4: 比赛统计数据**
1. 创建 `MatchStats` 模型
2. 扩展 API 调用（football-data.org 或 RapidAPI）
3. 集成到预测模型特征工程
4. 测试：查询"曼联对利物浦控球率"

### Week 3: Phase 3 - 高级数据扩展

**Task 5: 球队详细信息**
1. 扩展 `Team` 模型
2. 更新数据摄取逻辑
3. 测试：查询"曼联主教练是谁"

---

## 数据源对比

| 数据类型 | football-data.org (免费) | RapidAPI (付费) | Transfermarkt (爬虫) |
|---------|-------------------------|----------------|---------------------|
| 比赛基础数据 | ✅ 完整 | ✅ 完整 | ❌ 无 |
| 球员名单 | ✅ 有 | ✅ 完整 | ✅ 完整 |
| 球员统计 | ⚠️ 射手榜 | ✅ 详细 | ✅ 详细 |
| 积分榜 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| 比赛统计 | ⚠️ 有限 | ✅ 详细 | ❌ 无 |
| 阵容/首发 | ❌ 无 | ✅ 有 | ❌ 无 |
| 市值数据 | ❌ 无 | ⚠️ 部分 | ✅ 完整 |
| 转会数据 | ❌ 无 | ⚠️ 部分 | ✅ 完整 |

**建议策略**:
- **MVP 阶段**: 使用 football-data.org 免费 API（球员名单 + 积分榜 + 射手榜）
- **增长阶段**: 订阅 RapidAPI SofaScore（比赛详细统计 + 球员评分）
- **成熟阶段**: 爬虫 Transfermarkt（市值 + 转会数据）

---

## API 使用示例

### football-data.org API 端点

```bash
# 1. 获取球队详情（包含球员名单）
GET https://api.football-data.org/v4/teams/{id}

# 2. 获取积分榜
GET https://api.football-data.org/v4/competitions/{id}/standings

# 3. 获取射手榜
GET https://api.football-data.org/v4/competitions/{id}/scorers

# 4. 获取比赛详情
GET https://api.football-data.org/v4/matches/{id}
```

### 速率限制
- 免费版: 10 次/分钟
- 需要注意 API 配额管理

---

## 下一步行动

1. **立即执行**: 创建 `Player`、`Standing`、`PlayerSeasonStats` 模型
2. **编写迁移**: 使用 Alembic 生成数据库迁移文件
3. **扩展摄取脚本**: 添加新数据类型的抓取逻辑
4. **更新 Agent Tools**: 创建 `PlayerTool`、`StandingsTool` 等
5. **测试查询**: 验证新数据在 Agent 对话中的使用

---

## 预期效果

扩展后，用户可以询问：
- ✅ "哈兰德本赛季进了多少球？"
- ✅ "英超积分榜前五是哪些球队？"
- ✅ "曼联的主教练是谁？"
- ✅ "上一场曼联对利物浦的控球率是多少？"
- ✅ "阿森纳近五场比赛的平均射门次数"

这将大大提升 Agent 的专业性和实用性！

