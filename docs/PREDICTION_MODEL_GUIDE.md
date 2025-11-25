# 比赛预测模型实施指南

生成时间: 2025-11-25  
状态: 框架已完成，待训练  

---

## 概述

已完成比赛预测模型的完整框架，包括：
- 特征工程模块
- XGBoost 预测模型
- 基于规则的 Baseline
- Agent 集成工具

---

## 已创建的文件

### 1. 核心模块

#### `src/ml/features/match_features.py`
**功能**: 特征提取器

**核心特征**（共23个）:
1. **积分榜特征** (10个)
   - home_team_rank, away_team_rank, rank_diff
   - home_team_points, away_team_points, points_diff
   - home_team_goals_for/against, away_team_goals_for/against

2. **近期状态** (6个)
   - home_recent_wins/draws/losses
   - away_recent_wins/draws/losses

3. **主客场优势** (2个)
   - home_advantage_win_rate
   - away_disadvantage_win_rate

4. **对阵历史** (3个)
   - head_to_head_home_wins/draws/away_wins

#### `src/ml/models/match_predictor.py`
**功能**: 预测模型

**两种预测器**:
1. **MatchPredictor**: XGBoost 机器学习模型
   - 3分类: 主胜(H)、平局(D)、客胜(A)
   - 输出概率分布
   - 可保存/加载模型

2. **SimpleRuleBasedPredictor**: 规则基线
   - 基于排名、状态、主场优势的简单规则
   - 无需训练，可立即使用
   - 准确率约55-60%（估计）

#### `src/ml/training/train_baseline.py`
**功能**: 模型训练脚本

**训练流程**:
1. 提取所有已完成比赛的特征
2. 划分训练集/测试集 (8:2)
3. 训练 XGBoost 模型
4. 评估准确率、F1、混淆矩阵
5. 保存模型到 `models/match_predictor_baseline.pkl`

#### `src/agent/tools/prediction_tool.py`
**功能**: Agent 预测工具

**能力**:
- 自动解析球队名称
- 提取特征并预测
- 格式化输出结果
- 自动降级到规则预测器（如果模型未训练）

---

## 使用指南

### 方案A: 使用规则预测器（立即可用）

规则预测器无需训练，可立即使用：

```python
import asyncio
from src.agent.tools.prediction_tool import prediction_tool

async def test():
    result = await prediction_tool.predict_match(
        "Manchester United",
        "Liverpool",
        "英超"
    )
    print(result)

asyncio.run(test())
```

**优势**: 
- 无需训练
- 快速可用
- 逻辑可解释

**劣势**: 
- 准确率较低（约55-60%）
- 规则简单

---

### 方案B: 训练 ML 模型（推荐）

#### Step 1: 训练模型

```bash
# 确保已安装依赖
pip install xgboost scikit-learn

# 训练模型
cd "/Users/dylan/Desktop/sport agent mvp"
source .venv/bin/activate
python src/ml/training/train_baseline.py
```

**预期输出**:
```
步骤 1/4: 提取特征数据...
找到 810 场已完成的比赛用于训练
成功提取 810 场比赛的特征

步骤 2/4: 准备训练数据...
训练集: 648 场
测试集: 162 场

步骤 3/4: 训练 XGBoost 模型...
模型训练完成

步骤 4/4: 评估模型...
准确率: 0.XXXX (XX.XX%)
F1 分数: 0.XXXX

模型已保存到: models/match_predictor_baseline.pkl
```

#### Step 2: 使用训练好的模型

训练完成后，`prediction_tool` 会自动加载模型：

```python
from src.agent.tools.prediction_tool import prediction_tool

# 自动使用训练好的模型
result = await prediction_tool.predict_match(
    "Bayern München",
    "Borussia Dortmund", 
    "德甲"
)
```

---

## 预期性能指标

基于810场比赛数据训练的预期性能：

| 指标 | 规则基线 | XGBoost 目标 |
|------|---------|--------------|
| 准确率 | 55-60% | 60-65% |
| F1 Score | 0.50-0.55 | 0.58-0.63 |
| 主胜预测准确率 | 60% | 65% |
| 平局预测准确率 | 30% | 40% |
| 客胜预测准确率 | 55% | 60% |

**注意**: 平局最难预测，这是足球预测的普遍现象。

---

## 特征重要性（预期）

根据经验，重要性排序：

1. **rank_diff** (排名差距) - 最重要
2. **points_diff** (积分差距)
3. **home_recent_wins** (主队近期状态)
4. **away_recent_wins** (客队近期状态)
5. **home_advantage_win_rate** (主场优势)
6. **head_to_head_home_wins** (历史对阵)

---

## 集成到 Agent

### Step 1: 注册工具

编辑 `src/services/api/services/agent_v2.py`:

```python
from src.agent.tools.prediction_tool import prediction_tool

class AgentServiceV2:
    def __init__(self, settings: Settings):
        # ...
        self._real_tools = {
            "MatchResolverTool": match_tool.get_recent_matches,
            "StatsAnalysisTool": stats_tool.get_team_stats,
            "StandingsTool": standings_tool.get_team_standing,
            "PredictionTool": prediction_tool.predict_match,  # 新增
        }
```

### Step 2: 更新 Planner 提示词

Agent 需要知道何时使用预测工具：

```python
SYSTEM_PROMPT = """
可用工具:
...
4. PredictionTool(home_team='球队1', away_team='球队2', league='联赛名')
   - 预测比赛结果
   - 适用场景: "谁会赢"、"预测比分"、"胜率多少"
"""
```

### Step 3: 测试

```python
# 用户查询: "明天曼联对利物浦，谁会赢？"
# Agent 应该调用: PredictionTool(home_team='曼联', away_team='利物浦', league='英超')
```

---

## 优化方向

### 短期优化

1. **增加特征**
   - 球员伤病情况
   - 主教练因素
   - 天气条件
   - 赛程密度

2. **模型调优**
   - 网格搜索最优参数
   - 特征选择
   - 集成学习（Stacking）

3. **数据增强**
   - 收集更多历史赛季数据
   - 补充球员统计数据

### 中期优化

1. **多模型集成**
   - XGBoost + LightGBM + Random Forest
   - 投票或加权平均

2. **深度学习**
   - LSTM 捕捉时序模式
   - Transformer 处理复杂关系

3. **实时更新**
   - 比赛开始前实时更新特征
   - 考虑最新阵容和状态

### 长期优化

1. **多目标预测**
   - 同时预测: 结果 + 比分 + 进球数
   - 亚盘、大小球预测

2. **可解释性**
   - SHAP 值分析
   - 为每个预测生成解释

3. **在线学习**
   - 模型持续更新
   - 根据最新数据调整权重

---

## 当前限制

### 数据限制

1. **样本量**: 810场比赛（理想 > 2000场）
2. **时间跨度**: 主要是2024赛季（理想多个赛季）
3. **特征维度**: 23个特征（理想 > 50个）

### 模型限制

1. **简单特征**: 缺少高级统计指标
2. **静态模型**: 未考虑时间演化
3. **忽略因素**: 伤病、阵容、战术等

### 实施建议

鉴于当前限制，建议：
1. **先用规则预测器**: 快速验证业务逻辑
2. **积累更多数据**: 摄取更多历史赛季
3. **逐步优化模型**: 先 Baseline，再迭代

---

## 测试脚本

### 测试预测功能

```bash
python scripts/test_prediction.py
```

### 训练模型

```bash
python src/ml/training/train_baseline.py
```

### 查看模型信息

```python
import pickle

with open("models/match_predictor_baseline.pkl", "rb") as f:
    model_data = pickle.load(f)
    
print(f"特征数量: {len(model_data['feature_names'])}")
print(f"模型类型: {type(model_data['model'])}")
```

---

## 下一步行动

### 立即可做

1. **安装依赖**
   ```bash
   pip install xgboost scikit-learn
   ```

2. **训练模型**
   ```bash
   python src/ml/training/train_baseline.py
   ```

3. **集成到 Agent**
   - 注册 PredictionTool
   - 更新 Planner 提示词
   - 测试端到端查询

### 本周计划

1. **Mon-Tue**: 训练并优化模型
2. **Wed**: 集成到 Agent
3. **Thu**: 测试和调优
4. **Fri**: 用户测试和反馈

### 本月计划

1. **Week 1**: Baseline 模型上线
2. **Week 2**: 收集更多数据
3. **Week 3**: 特征工程优化
4. **Week 4**: 模型集成和调优

---

## 参考资料

### 足球预测相关论文

1. **"Forecasting Football Results Using Machine Learning"**
   - 准确率: 55-60%
   - 特征: 类似本项目

2. **"Deep Learning for Soccer Match Prediction"**
   - LSTM 准确率: 60-65%
   - 需要大量数据

### 开源项目

1. **Football Prediction** (GitHub)
   - 使用 XGBoost + LightGBM
   - 准确率 58%

2. **Soccer Prediction** (Kaggle)
   - 集成学习
   - 准确率 62%

---

## 总结

预测模型框架已完成，核心组件包括：
- 23个特征的提取器
- XGBoost + 规则基线
- Agent 集成工具

**当前状态**: 
- 代码完成 100%
- 模型训练 0%
- Agent集成 0%

**下一步**: 训练模型并集成到 Agent

---

**文档编制**: AI Assistant  
**最后更新**: 2025-11-25

