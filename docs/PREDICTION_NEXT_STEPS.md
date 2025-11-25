# 预测模型下一步行动指南

当前状态: 模型准确率47.86%，需要优化  
生成时间: 2025-11-25

---

## 问题总结

您刚才训练的模型准确率只有**47.86%**，接近随机猜测。核心问题是：

###  1. 积分榜数据时间错配

**当前问题**: 使用的是赛季末的最终排名，而不是比赛当时的排名

```
8月10日的比赛 MUN vs LIV
├── 使用积分榜: 2024赛季结束时的排名（错误！）
└── 应该使用: 8月10日当天的实时排名
```

**影响**: 模型学到了错误的特征关联，导致预测不准

---

### 2. 历史数据不足

**当前问题**: 赛季初期的比赛没有历史数据

```
8月的比赛:
├── 近期5场: 0胜0平0负（全是0）
├── 主场优势: 0.5（默认值）
└── 对阵历史: 0胜0平0负（全是0）
```

**影响**: 大量特征为0，模型无法学习

---

## 解决方案

### 方案1: 实现动态积分榜（推荐）

**核心思路**: 从历史比赛实时计算截至某日期的积分榜

#### 实施步骤

1. **创建动态积分榜计算器**

创建 `src/ml/features/dynamic_standings.py`:

```python
"""
动态积分榜计算器

根据历史比赛结果计算任意时间点的积分榜
"""
from typing import Dict, List
from datetime import datetime
from sqlalchemy import select, and_
from src.infra.db.models import Match
from src.infra.db.session import AsyncSessionLocal


class DynamicStandingsCalculator:
    """动态积分榜计算器"""
    
    async def calculate_standings_at_date(
        self,
        league_id: str,
        date: datetime,
        season: str = "2024"
    ) -> Dict[str, Dict]:
        """
        计算截至指定日期的积分榜
        
        Args:
            league_id: 联赛ID
            date: 截止日期
            season: 赛季
            
        Returns:
            {team_id: {position: int, points: int, ...}}
        """
        async with AsyncSessionLocal() as db:
            # 1. 查询该日期之前的所有已完成比赛
            stmt = select(Match).where(
                and_(
                    Match.league_id == league_id,
                    Match.match_date < date,
                    Match.status == "FINISHED",
                    Match.result.isnot(None)
                )
            ).order_by(Match.match_date)
            
            result = await db.execute(stmt)
            matches = result.scalars().all()
            
            # 2. 统计各队数据
            team_stats = {}
            for match in matches:
                # 初始化球队数据
                for team_id in [match.home_team_id, match.away_team_id]:
                    if team_id not in team_stats:
                        team_stats[team_id] = {
                            'played': 0,
                            'wins': 0,
                            'draws': 0,
                            'losses': 0,
                            'goals_for': 0,
                            'goals_against': 0,
                            'points': 0
                        }
                
                # 更新主队数据
                home_stats = team_stats[match.home_team_id]
                away_stats = team_stats[match.away_team_id]
                
                home_stats['played'] += 1
                away_stats['played'] += 1
                
                home_stats['goals_for'] += match.home_score or 0
                home_stats['goals_against'] += match.away_score or 0
                away_stats['goals_for'] += match.away_score or 0
                away_stats['goals_against'] += match.home_score or 0
                
                if match.result == 'H':
                    home_stats['wins'] += 1
                    home_stats['points'] += 3
                    away_stats['losses'] += 1
                elif match.result == 'D':
                    home_stats['draws'] += 1
                    home_stats['points'] += 1
                    away_stats['draws'] += 1
                    away_stats['points'] += 1
                else:  # 'A'
                    away_stats['wins'] += 1
                    away_stats['points'] += 3
                    home_stats['losses'] += 1
            
            # 3. 按积分排序生成排名
            sorted_teams = sorted(
                team_stats.items(),
                key=lambda x: (
                    x[1]['points'],
                    x[1]['goals_for'] - x[1]['goals_against'],
                    x[1]['goals_for']
                ),
                reverse=True
            )
            
            # 4. 添加排名
            standings = {}
            for rank, (team_id, stats) in enumerate(sorted_teams, 1):
                stats['position'] = rank
                stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
                standings[team_id] = stats
            
            return standings


# 全局单例
dynamic_standings_calculator = DynamicStandingsCalculator()
```

2. **修改特征提取器使用动态积分榜**

修改 `src/ml/features/match_features.py`:

```python
# 在文件顶部导入
from src.ml.features.dynamic_standings import dynamic_standings_calculator

class MatchFeatureExtractor:
    # ...
    
    async def _get_standing_features(
        self,
        db: AsyncSession,
        home_team_id: str,
        away_team_id: str,
        league_id: str,
        season: str,
        match_date: datetime  # 新增参数
    ) -> Dict[str, float]:
        """提取积分榜特征（使用动态积分榜）"""
        
        # 使用动态积分榜
        standings = await dynamic_standings_calculator.calculate_standings_at_date(
            league_id, match_date, season
        )
        
        home_standing = standings.get(home_team_id)
        away_standing = standings.get(away_team_id)
        
        if home_standing and away_standing:
            features["home_team_rank"] = float(home_standing['position'])
            features["away_team_rank"] = float(away_standing['position'])
            # ...其他特征
        else:
            # 默认值
            # ...
        
        return features
```

**预期效果**: 准确率提升到 55-60%

---

### 方案2: 摄取历史赛季数据

**核心思路**: 摄取2023赛季数据，让2024年8月的比赛有历史数据

#### 实施步骤

修改 `src/data_pipeline/ingest_football_data_v2.py`:

```python
# 增加摄取历史赛季的功能
async def ingest_historical_season(self, league_code: str, season_year: int):
    """摄取历史赛季数据"""
    # API调用获取历史数据
    # ...
```

运行:
```bash
python -c "
import asyncio
from src.data_pipeline.ingest_football_data_v2 import FootballDataIngester

async def main():
    ingester = FootballDataIngester()
    # 摄取2023赛季
    await ingester.ingest_historical_season('PL', 2023)
    await ingester.ingest_historical_season('BL1', 2023)
    # ...

asyncio.run(main())
"
```

**预期效果**: 
- 训练样本增加到1500+
- 准确率提升到 58-62%

---

### 方案3: 简化特征（快速修复）

**核心思路**: 只使用质量高的特征，移除依赖历史的特征

修改 `src/ml/features/match_features.py`:

```python
class MatchFeatureExtractor:
    def __init__(self, use_history_features: bool = True):
        base_features = [
            "home_team_rank",
            "away_team_rank",
            "rank_diff",
            "home_team_points",
            "away_team_points",
            "points_diff",
            "home_team_goals_for",
            "away_team_goals_for",
            "home_team_goals_against",
            "away_team_goals_against",
        ]
        
        if use_history_features:
            # 添加历史相关特征
            base_features.extend([
                "home_recent_wins",
                "home_recent_draws",
                # ...
            ])
        
        self.feature_names = base_features
```

训练时:
```python
feature_extractor = MatchFeatureExtractor(use_history_features=False)
```

**预期效果**: 准确率提升到 50-52%

---

## 立即行动

### 选项A: 快速测试方案3（5分钟）

1. 修改特征提取器，移除历史特征
2. 重新训练
3. 查看准确率是否提升到50%+

### 选项B: 实施方案1（1小时）

1. 创建 `dynamic_standings.py`
2. 修改特征提取器
3. 重新训练
4. 查看准确率是否提升到55%+

### 选项C: 暂时使用规则预测器

当前规则预测器虽然简单，但逻辑清晰，可以先用它：

```python
# src/agent/tools/prediction_tool.py 会自动使用规则预测器
# 如果模型准确率太低，可以强制使用规则预测器

class PredictionTool:
    def __init__(self, model_path: str = None):
        # 强制使用规则预测器
        self.predictor = SimpleRuleBasedPredictor()
        self.use_ml_model = False
```

规则预测器预期准确率: 52-55%（可能比当前模型更好）

---

## 推荐路径

### 短期（今天）

1. **暂时使用规则预测器**
   - 准确率: 52-55%
   - 优点: 立即可用，逻辑可解释
   - 缺点: 上限较低

2. **集成到 Agent**
   - 先让功能跑起来
   - 积累用户反馈

### 中期（本周）

1. **实施方案1: 动态积分榜**
   - 预期准确率: 55-60%
   - 工作量: 1-2小时

2. **重新训练和评估**

### 长期（下周）

1. **实施方案2: 历史数据**
   - 预期准确率: 60-65%
   - 工作量: 3-4小时

2. **特征工程优化**
3. **模型调优**

---

## 总结

| 方案 | 工作量 | 预期准确率 | 优先级 |
|------|--------|-----------|--------|
| 方案3: 简化特征 | 5分钟 | 50-52% | P1 |
| 规则预测器 | 0分钟 | 52-55% | P0 |
| 方案1: 动态积分榜 | 1小时 | 55-60% | P0 |
| 方案2: 历史数据 | 3小时 | 60-65% | P1 |

**建议**: 
1. 立即：使用规则预测器，集成到Agent
2. 本周：实施动态积分榜
3. 下周：摄取历史数据

这样可以快速上线功能，然后逐步优化模型。

---

**下一步**: 告诉我您想选择哪个方案，我马上帮您实施。

