"""
训练比赛预测模型 Baseline

使用历史比赛数据训练 XGBoost 模型
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

from src.ml.features.match_features import MatchFeatureExtractor
from src.ml.models.match_predictor import MatchPredictor


async def main():
    """训练主函数"""
    print("=" * 80)
    print("比赛预测模型训练 - Baseline")
    print("=" * 80)
    
    # 1. 提取特征
    print("\n步骤 1/4: 提取特征数据...")
    feature_extractor = MatchFeatureExtractor()
    
    # 提取所有已完成比赛的特征
    # 注意: 为了让早期比赛也有足够的历史数据，我们不设置min_date
    # 或者设置一个较晚的日期（比如10月）确保有足够的历史数据
    df = await feature_extractor.extract_training_dataset(
        league_id=None,  # 所有联赛
        season="2024",
        min_date=datetime(2024, 10, 1)  # 从2024年10月开始，确保有历史数据
    )
    
    if len(df) < 50:
        print(f"警告: 数据量过少 ({len(df)} 场)，建议至少100场以上")
        print("请先运行数据摄取脚本获取更多数据")
        return
    
    print(f"成功提取 {len(df)} 场比赛的特征")
    
    # 2. 准备训练数据
    print("\n步骤 2/4: 准备训练数据...")
    
    # 移除非特征列
    feature_cols = feature_extractor.feature_names
    X = df[feature_cols].values
    y = df['label'].values
    
    # 检查缺失值
    if np.any(np.isnan(X)):
        print("警告: 发现缺失值，使用0填充")
        X = np.nan_to_num(X, 0)
    
    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"训练集: {len(X_train)} 场")
    print(f"测试集: {len(X_test)} 场")
    print(f"类别分布: {pd.Series(y_train).value_counts().to_dict()}")
    
    # 3. 训练模型
    print("\n步骤 3/4: 训练 XGBoost 模型...")
    
    predictor = MatchPredictor()
    predictor.feature_names = feature_cols
    
    # XGBoost 参数
    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'max_depth': 5,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'eval_metric': 'mlogloss'
    }
    
    try:
        predictor.train(
            X_train, y_train,
            X_test, y_test,
            params=params
        )
    except ImportError as e:
        print(f"错误: {e}")
        print("请先安装 XGBoost: pip install xgboost scikit-learn")
        return
    
    # 4. 评估模型
    print("\n步骤 4/4: 评估模型...")
    
    predictions, probabilities = predictor.predict(X_test)
    
    # 准确率
    accuracy = accuracy_score(y_test, predictions)
    print(f"\n准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")
    
    # F1 分数
    f1 = f1_score(y_test, predictions, average='weighted')
    print(f"F1 分数: {f1:.4f}")
    
    # 分类报告
    print("\n分类报告:")
    print(classification_report(y_test, predictions, target_names=['主胜(H)', '平局(D)', '客胜(A)']))
    
    # 混淆矩阵
    cm = confusion_matrix(y_test, predictions, labels=['H', 'D', 'A'])
    print("\n混淆矩阵:")
    print("          预测")
    print("         H    D    A")
    print(f"实际 H  {cm[0][0]:4} {cm[0][1]:4} {cm[0][2]:4}")
    print(f"     D  {cm[1][0]:4} {cm[1][1]:4} {cm[1][2]:4}")
    print(f"     A  {cm[2][0]:4} {cm[2][1]:4} {cm[2][2]:4}")
    
    # 特征重要性
    print("\n特征重要性 (Top 10):")
    importance = predictor.get_feature_importance()
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for name, score in sorted_importance[:10]:
        print(f"  {name:30} {score:.4f}")
    
    # 5. 保存模型
    model_path = "models/match_predictor_baseline.pkl"
    Path("models").mkdir(exist_ok=True)
    predictor.save_model(model_path)
    
    print("\n" + "=" * 80)
    print("训练完成!")
    print(f"模型已保存到: {model_path}")
    print(f"准确率: {accuracy*100:.2f}%")
    print("=" * 80)
    
    # 6. 测试预测
    print("\n测试预测示例:")
    test_sample = df.iloc[0]
    features = {col: test_sample[col] for col in feature_cols}
    result = predictor.predict_single(features)
    
    print(f"比赛: {test_sample['home_team_id']} vs {test_sample['away_team_id']}")
    print(f"实际结果: {test_sample['label']}")
    print(f"预测结果: {result['prediction']}")
    print(f"预测概率: 主胜 {result['probabilities']['home_win']:.2%}, "
          f"平局 {result['probabilities']['draw']:.2%}, "
          f"客胜 {result['probabilities']['away_win']:.2%}")
    print(f"置信度: {result['confidence']:.2%}")


if __name__ == "__main__":
    asyncio.run(main())

