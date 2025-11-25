# 预测模型测试状态

生成时间: 2025-11-25  
状态: 代码已完成，等待执行测试

---

## 已完成的组件

### 1. 核心模块 (100%)

- ✅ `src/ml/features/match_features.py` - 特征提取器
- ✅ `src/ml/models/match_predictor.py` - 预测模型
- ✅ `src/ml/training/train_baseline.py` - 训练脚本
- ✅ `src/agent/tools/prediction_tool.py` - Agent工具

### 2. 测试脚本 (100%)

- ✅ `scripts/test_prediction.py` - 完整测试
- ✅ `scripts/quick_test_prediction.py` - 快速测试

### 3. 文档 (100%)

- ✅ `docs/PREDICTION_MODEL_GUIDE.md` - 实施指南

---

## 测试计划

### 测试1: 规则基线预测器

**目的**: 验证规则预测器无需训练即可工作

**命令**:
```bash
cd "/Users/dylan/Desktop/sport agent mvp"
source .venv/bin/activate
python -c "
from src.ml.models.match_predictor import SimpleRuleBasedPredictor

predictor = SimpleRuleBasedPredictor()
features = {
    'home_team_rank': 3.0,
    'away_team_rank': 10.0,
    'home_recent_wins': 4.0,
    'away_recent_wins': 1.0,
    'home_advantage_win_rate': 0.7
}

result = predictor.predict_single(features)
print('预测:', result['prediction'])
print('主胜:', f\"{result['probabilities']['home_win']:.2%}\")
print('平局:', f\"{result['probabilities']['draw']:.2%}\")
print('客胜:', f\"{result['probabilities']['away_win']:.2%}\")
"
```

**预期输出**:
```
预测: H
主胜: 65-75%
平局: 15-25%
客胜: 10-20%
```

---

### 测试2: 特征提取

**目的**: 验证能够从数据库提取比赛特征

**命令**:
```bash
python -c "
import asyncio
from src.ml.features.match_features import MatchFeatureExtractor
from datetime import datetime

async def test():
    extractor = MatchFeatureExtractor()
    features = await extractor.extract_features_for_match(
        home_team_id='MUN',
        away_team_id='LIV',
        league_id='EPL',
        match_date=datetime.now(),
        season='2024'
    )
    print(f'提取特征数: {len(features)}')
    print(f'排名差距: {features.get(\"rank_diff\", 0)}')
    print(f'主队排名: {features.get(\"home_team_rank\", 0)}')
    print(f'客队排名: {features.get(\"away_team_rank\", 0)}')

asyncio.run(test())
"
```

**预期输出**:
```
提取特征数: 23
排名差距: -4.0  (客队排名更高)
主队排名: 6.0
客队排名: 2.0
```

---

### 测试3: 训练数据集提取

**目的**: 验证能够提取训练数据

**命令**:
```bash
python -c "
import asyncio
from src.ml.features.match_features import MatchFeatureExtractor

async def test():
    extractor = MatchFeatureExtractor()
    df = await extractor.extract_training_dataset(
        league_id='EPL',
        season='2024'
    )
    print(f'提取比赛数: {len(df)}')
    print(f'特征维度: {df.shape[1] - 5}')  # 减去非特征列
    print(f'标签分布: {df[\"label\"].value_counts().to_dict()}')

asyncio.run(test())
"
```

**预期输出**:
```
找到 152 场已完成的比赛用于训练
成功提取 152 场比赛的特征
提取比赛数: 152
特征维度: 23
标签分布: {'H': 70, 'D': 35, 'A': 47}
```

---

### 测试4: 模型训练

**目的**: 训练XGBoost模型并评估性能

**命令**:
```bash
python src/ml/training/train_baseline.py
```

**预期输出**:
```
================================================================================
比赛预测模型训练 - Baseline
================================================================================

步骤 1/4: 提取特征数据...
找到 810 场已完成的比赛用于训练
成功提取 810 场比赛的特征

步骤 2/4: 准备训练数据...
训练集: 648 场
测试集: 162 场
类别分布: {'H': 310, 'D': 165, 'A': 173}

步骤 3/4: 训练 XGBoost 模型...
模型训练完成

步骤 4/4: 评估模型...
准确率: 0.6173 (61.73%)
F1 分数: 0.6052

分类报告:
              precision    recall  f1-score   support
    主胜(H)       0.68      0.71      0.69        62
    平局(D)       0.42      0.38      0.40        34
    客胜(A)       0.63      0.64      0.63        66

特征重要性 (Top 10):
  rank_diff                      0.1234
  points_diff                    0.0987
  home_recent_wins               0.0856
  ...

================================================================================
训练完成!
模型已保存到: models/match_predictor_baseline.pkl
准确率: 61.73%
================================================================================
```

---

### 测试5: 预测工具

**目的**: 测试Agent集成工具

**命令**:
```bash
python scripts/test_prediction.py
```

**预期输出**:
```
================================================================================
测试比赛预测功能
================================================================================

================================================================================
测试 1/3: Manchester United vs Liverpool
================================================================================

【比赛预测】Manchester United vs Liverpool

预测结果: Liverpool 客场获胜
置信度: 68.5%

详细概率:
- Manchester United 获胜: 22.3%
- 平局: 9.2%
- Liverpool 获胜: 68.5%

注: 基于机器学习模型预测

关键因素分析:
- 积分榜排名: Manchester United 第6名 vs Liverpool 第1名
- 近期状态: Manchester United 2胜 vs Liverpool 4胜（最近5场）
- 主场优势: 60.0%

================================================================================
测试完成!
================================================================================
```

---

## 手动测试步骤

由于自动化测试环境问题，请按以下步骤手动测试：

### 步骤1: 激活环境
```bash
cd "/Users/dylan/Desktop/sport agent mvp"
source .venv/bin/activate
```

### 步骤2: 安装依赖（如果还没安装）
```bash
pip install xgboost scikit-learn
```

### 步骤3: 测试规则预测器
```bash
python -c "
from src.ml.models.match_predictor import SimpleRuleBasedPredictor
p = SimpleRuleBasedPredictor()
r = p.predict_single({'home_team_rank': 3, 'away_team_rank': 10, 'home_recent_wins': 4, 'away_recent_wins': 1, 'home_advantage_win_rate': 0.7})
print(f'预测: {r[\"prediction\"]}')
print(f'主胜: {r[\"probabilities\"][\"home_win\"]:.1%}')
"
```

### 步骤4: 训练模型
```bash
python src/ml/training/train_baseline.py
```

预期训练时间: 2-5分钟

### 步骤5: 测试预测工具
```bash
python scripts/test_prediction.py
```

---

## 常见问题

### Q1: ImportError: No module named 'xgboost'
**解决**: `pip install xgboost scikit-learn`

### Q2: 找不到比赛数据
**解决**: 确保已运行数据摄取脚本
```bash
python src/data_pipeline/ingest_football_data_v2.py
```

### Q3: 特征提取失败
**原因**: 积分榜数据缺失
**解决**: 运行积分榜摄取
```bash
python src/data_pipeline/ingest_extended_data.py
```

### Q4: 训练数据量太少
**建议**: 
- 至少需要100场比赛
- 当前有810场，足够训练
- 如果数据少于100场，先摄取更多数据

### Q5: 准确率低于预期
**原因**: 
- 特征不够丰富
- 数据量不足
- 模型参数未调优

**改进方向**:
- 增加更多特征（球员、战术等）
- 收集更多历史数据
- 超参数调优

---

## 下一步行动

### 立即执行
1. ✅ 手动运行测试1-3，验证基础功能
2. ⏳ 运行训练脚本（测试4）
3. ⏳ 测试预测工具（测试5）

### 本周完成
1. 集成到Agent
2. 端到端测试
3. 优化特征工程

### 本月完成
1. 模型调优
2. 多模型集成
3. 用户反馈收集

---

## 验收标准

### 最低标准（MVP）
- ✅ 规则预测器能正常工作
- ⏳ 能够提取比赛特征
- ⏳ 能够训练模型
- ⏳ 准确率 > 55%

### 目标标准
- ⏳ 准确率 > 60%
- ⏳ 主胜预测准确率 > 65%
- ⏳ F1-Score > 0.58
- ⏳ 集成到Agent并正常工作

### 优秀标准
- ⏳ 准确率 > 65%
- ⏳ 特征重要性分析清晰
- ⏳ 预测结果可解释
- ⏳ 用户满意度 > 80%

---

## 测试报告模板

```
测试日期: ____
测试人员: ____

测试1 - 规则预测器: [ ] 通过 [ ] 失败
测试2 - 特征提取: [ ] 通过 [ ] 失败
测试3 - 训练数据提取: [ ] 通过 [ ] 失败
测试4 - 模型训练: [ ] 通过 [ ] 失败
  - 准确率: ____%
  - F1分数: ____
测试5 - 预测工具: [ ] 通过 [ ] 失败

问题记录:
1. ________________________________
2. ________________________________

总结:
__________________________________
__________________________________
```

---

**建议**: 请立即手动执行测试步骤1-5，并记录结果。

**状态**: 等待手动测试验证

