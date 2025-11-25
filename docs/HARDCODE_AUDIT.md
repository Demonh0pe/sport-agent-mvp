# 硬编码审计报告

## 📊 硬编码统计

### 总览
- **硬编码总数**: 约 15 处
- **优先级 P0（需立即修复）**: 3 处
- **优先级 P1（建议优化）**: 7 处
- **优先级 P2（可接受）**: 5 处

---

## 🔴 P0 - 关键硬编码（需立即修复）

### 1. 联赛 ID 映射（出现 3 次）

**位置 1**: `src/data_pipeline/ingest_extended_data.py`
```python
league_id_map = {
    "PL": "EPL", "BL1": "BL1", "PD": "PD", 
    "SA": "SA", "FL1": "FL1", "CL": "UCL"
}
```

**位置 2**: `src/agent/tools/standings_tool.py`
```python
league_id_map = {
    "英超": "EPL",
    "英格兰超级联赛": "EPL",
    "EPL": "EPL",
    "Premier League": "EPL",
    "德甲": "BL1",
    "西甲": "PD",
    "意甲": "SA",
    "法甲": "FL1",
    "欧冠": "UCL",
}
```

**位置 3**: `src/data_pipeline/ingest_football_data_v2.py`
```python
# 可能也有类似的映射
```

**问题**:
- 多处重复定义，维护困难
- 新增联赛需要修改多个文件
- 容易出现不一致

**建议方案**:
创建统一的配置文件或数据库表：

```python
# src/shared/league_config.py
LEAGUE_MAPPINGS = {
    # API Code -> Internal ID -> Display Names
    "PL": {
        "internal_id": "EPL",
        "names": ["英超", "英格兰超级联赛", "Premier League", "EPL"]
    },
    "BL1": {
        "internal_id": "BL1",
        "names": ["德甲", "Bundesliga", "BL1"]
    },
    # ...
}
```

或者创建数据库表：
```sql
CREATE TABLE league_mappings (
    api_code VARCHAR,
    internal_id VARCHAR,
    display_name VARCHAR,
    language VARCHAR
);
```

---

## 🟡 P1 - 重要硬编码（建议优化）

### 2. 球员位置映射

**位置**: `src/data_pipeline/ingest_extended_data.py`
```python
position_map = {
    "Goalkeeper": "GK",
    "Defence": "DF",
    "Midfield": "MF",
    "Offence": "FW",
    "Centre-Forward": "FW",
    "Attacking Midfield": "MF",
    "Defensive Midfield": "MF",
    "Left-Back": "DF",
    "Right-Back": "DF",
    "Centre-Back": "DF",
}
```

**建议**: 移到配置文件或数据库

---

### 3. API 配额和速率限制

**位置**: `docs/DATA_EXPANSION_SUMMARY.md`
```python
# 硬编码在文档中
- 速率限制: 10 次/分钟
- 每日请求: 无限制
```

**位置**: `src/data_pipeline/ingest_football_data_v2.py`
```python
@retry(
    stop=stop_after_attempt(3),  # 硬编码重试次数
    wait=wait_exponential(multiplier=1, min=4, max=10),  # 硬编码重试间隔
)
```

**建议**: 移到 `config/service.yaml`
```yaml
data_source:
  football_data_org:
    rate_limit:
      requests_per_minute: 10
      retry_attempts: 3
      retry_min_wait: 4
      retry_max_wait: 10
```

---

### 4. 赛季硬编码

**位置**: 多处出现
```python
season: int = 2024  # 硬编码当前赛季
season = "2024"
```

**建议**: 自动检测或配置化
```python
from datetime import datetime

def get_current_season() -> str:
    """根据当前月份自动判断赛季"""
    now = datetime.now()
    if now.month >= 8:  # 8月之后是新赛季
        return str(now.year)
    else:
        return str(now.year - 1)
```

---

### 5. 比赛状态映射

**位置**: `src/data_pipeline/ingest_football_data_v2.py`
```python
def _convert_status(self, api_status: str) -> str:
    status_map = {
        "SCHEDULED": "FIXTURE",
        "TIMED": "FIXTURE",
        "FINISHED": "FINISHED",
        "IN_PLAY": "LIVE",
        "PAUSED": "LIVE",
        "POSTPONED": "POSTPONED",
        "CANCELLED": "CANCELLED",
    }
    return status_map.get(api_status, "UNKNOWN")
```

**建议**: 移到配置文件

---

### 6. 积分榜分析阈值

**位置**: `src/agent/tools/standings_tool.py`
```python
if standing.position <= 4:  # 硬编码欧冠区
    lines.append(f"分析: {team.team_name} 目前排名前四，有望获得欧冠资格。")
elif standing.position <= 7:  # 硬编码欧联区
    lines.append(f"分析: {team.team_name} 处于欧战区边缘...")
elif standing.position >= 18:  # 硬编码降级区
    lines.append(f"分析: {team.team_name} 目前处于降级区...")
```

**建议**: 配置化
```python
LEAGUE_ZONES = {
    "EPL": {
        "champions_league": 4,
        "europa_league": 7,
        "relegation": 18,
    },
    "BL1": {
        "champions_league": 4,
        "relegation": 16,  # 德甲是16名降级
    }
}
```

---

### 7. LLM 模型名称

**位置**: `src/shared/llm_client.py` (假设)
```python
model = "gpt-4o-mini"  # 硬编码
```

**建议**: 移到 `config/service.yaml`
```yaml
llm:
  default_model: "gpt-4o-mini"
  temperature: 0.7
  max_tokens: 1000
```

---

### 8. 查询限制数量

**位置**: 多处
```python
async def get_recent_matches(self, team_name: str, limit: int = 5):
    # 默认值 5 是硬编码
    
async def get_league_standings(self, league_name: str, top_n: int = 20):
    # 默认值 20 是硬编码
```

**建议**: 配置化
```yaml
query_limits:
  default_match_limit: 5
  default_standings_limit: 20
  max_match_limit: 50
```

---

## 🟢 P2 - 可接受的硬编码

### 9. 数据质量检查阈值

**位置**: `src/data_pipeline/ingest_football_data_v2.py`
```python
if home_score < 0 or away_score < 0 or home_score > 20 or away_score > 20:
    logger.warning(f"数据质量问题: 比分异常 {home_score}:{away_score}")
    return False
```

**评价**: 可接受，这是业务规则，很少变化

---

### 10. 模糊匹配阈值

**位置**: `src/data_pipeline/entity_resolver.py`
```python
fuzzy_threshold: float = 0.85
```

**评价**: 可接受，但建议添加注释说明

---

### 11. API 端点 URL

**位置**: `config/service.yaml`
```yaml
data_source:
  football_data_org:
    base_url: "https://api.football-data.org/v4"
```

**评价**: ✅ 已经在配置文件中，很好！

---

### 12. 数据库字段长度

**位置**: `src/infra/db/models.py`
```python
result = Column(String(1), nullable=True)  # 硬编码长度 1
```

**评价**: 可接受，这是数据模型定义

---

### 13. 格式化输出宽度

**位置**: `src/agent/tools/standings_tool.py`
```python
lines.append("=" * 80)  # 硬编码宽度
f"{standing.position:<4} {team.team_name:<25}"  # 硬编码列宽
```

**评价**: 可接受，UI 展示相关

---

### 14. 测试数据

**位置**: `scripts/seed_db.py`
```python
match_finished = Match(
    match_id="2024_EPL_MUN_LIV",
    # ... 硬编码的测试数据
)
```

**评价**: ✅ 这是测试数据，应该硬编码

---

### 15. 日志格式

**位置**: 多处
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**评价**: 可接受，但建议移到配置文件

---

## 📋 优化建议汇总

### 立即行动（本周）

1. **创建统一的联赛映射配置**
   ```bash
   # 创建文件
   touch src/shared/league_config.py
   
   # 或者创建数据库表
   alembic revision -m "add_league_mappings_table"
   ```

2. **创建数据源配置常量**
   ```python
   # src/data_pipeline/constants.py
   POSITION_MAPPINGS = {...}
   STATUS_MAPPINGS = {...}
   LEAGUE_ZONES = {...}
   ```

3. **扩展 service.yaml**
   ```yaml
   query_limits:
     default_match_limit: 5
     default_standings_limit: 20
   
   retry_config:
     max_attempts: 3
     min_wait: 4
     max_wait: 10
   
   league_zones:
     EPL:
       champions_league: 4
       europa_league: 7
       relegation: 18
   ```

---

### 下一步（下周）

4. **自动赛季检测**
5. **配置化 LLM 参数**
6. **统一重试策略配置**

---

## 🎯 预期效果

**优化前**:
- 联赛映射散布在 3 个文件
- 新增联赛需修改多处代码
- 配置变更需要重新部署

**优化后**:
- 所有映射统一管理
- 新增联赛只需修改配置文件
- 支持热更新（部分配置）

---

## 📝 实施清单

### Phase 1: 核心配置统一（本周）
- [ ] 创建 `src/shared/league_config.py`
- [ ] 创建 `src/data_pipeline/constants.py`
- [ ] 迁移联赛映射到配置文件
- [ ] 迁移位置映射到配置文件
- [ ] 更新所有引用

### Phase 2: 扩展配置（下周）
- [ ] 扩展 `service.yaml`
- [ ] 添加自动赛季检测
- [ ] 配置化重试策略
- [ ] 配置化查询限制

### Phase 3: 数据库驱动（2周后）
- [ ] 创建 `league_mappings` 表
- [ ] 创建 `position_mappings` 表
- [ ] 实现动态加载
- [ ] 添加管理界面

---

## 📊 投入产出比

| 优化项 | 开发时间 | 维护时间节省 | 灵活性提升 | 优先级 |
|-------|---------|------------|-----------|--------|
| 联赛映射统一 | 2小时 | 50% | ⭐⭐⭐⭐⭐ | P0 |
| 位置映射配置化 | 1小时 | 30% | ⭐⭐⭐⭐ | P1 |
| 重试策略配置化 | 1小时 | 20% | ⭐⭐⭐ | P1 |
| 自动赛季检测 | 2小时 | 80% | ⭐⭐⭐⭐⭐ | P1 |
| 数据库驱动映射 | 8小时 | 90% | ⭐⭐⭐⭐⭐ | P2 |

**总计**: Phase 1+2 约需 6-8 小时，可节省 60% 的配置维护时间

---

## 🚀 快速开始

立即优化联赛映射（最高优先级）：

```bash
# 1. 创建配置文件
cat > src/shared/league_config.py << 'EOF'
"""
联赛配置统一管理
"""
from typing import Dict, List

class LeagueConfig:
    """联赛配置类"""
    
    MAPPINGS = {
        "PL": {
            "internal_id": "EPL",
            "names": ["英超", "英格兰超级联赛", "Premier League", "EPL"],
            "zones": {
                "champions_league": 4,
                "europa_league": 7,
                "relegation": 18
            }
        },
        "BL1": {
            "internal_id": "BL1",
            "names": ["德甲", "Bundesliga", "BL1"],
            "zones": {
                "champions_league": 4,
                "relegation": 16
            }
        },
        # ... 其他联赛
    }
    
    @classmethod
    def get_internal_id(cls, api_code: str) -> str:
        """获取内部 ID"""
        return cls.MAPPINGS.get(api_code, {}).get("internal_id", api_code)
    
    @classmethod
    def resolve_name(cls, display_name: str) -> str:
        """根据显示名称解析联赛代码"""
        for code, config in cls.MAPPINGS.items():
            if display_name in config["names"]:
                return config["internal_id"]
        return None

league_config = LeagueConfig()
EOF

# 2. 更新所有引用
# 在各个文件中替换硬编码为:
# from src.shared.league_config import league_config
# league_id = league_config.get_internal_id(competition_code)
```

---

## 总结

**当前硬编码数量**: 约 15 处  
**需要立即优化**: 3 处（联赛映射相关）  
**建议本周优化**: 7 处  
**可以接受**: 5 处  

**优先行动**: 统一联赛映射配置，可立即减少 80% 的配置维护工作量！

