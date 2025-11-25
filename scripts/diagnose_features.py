"""
诊断特征提取问题
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.ml.features.match_features import MatchFeatureExtractor


async def main():
    print("=" * 80)
    print("诊断特征提取")
    print("=" * 80)
    
    extractor = MatchFeatureExtractor()
    
    # 提取训练数据
    df = await extractor.extract_training_dataset(
        league_id=None,
        season="2024",
        min_date=datetime(2024, 8, 1)
    )
    
    print(f"\n数据集大小: {len(df)} 场比赛")
    print(f"特征数量: {len(extractor.feature_names)}")
    
    # 检查特征统计
    print("\n" + "=" * 80)
    print("特征统计")
    print("=" * 80)
    
    for feature in extractor.feature_names[:10]:  # 显示前10个特征
        values = df[feature]
        print(f"\n{feature}:")
        print(f"  均值: {values.mean():.4f}")
        print(f"  标准差: {values.std():.4f}")
        print(f"  最小值: {values.min():.4f}")
        print(f"  最大值: {values.max():.4f}")
        print(f"  零值占比: {(values == 0).sum() / len(values):.2%}")
    
    # 检查标签分布
    print("\n" + "=" * 80)
    print("标签分布")
    print("=" * 80)
    print(df['label'].value_counts())
    
    # 检查是否有太多零值
    print("\n" + "=" * 80)
    print("零值特征统计")
    print("=" * 80)
    zero_features = []
    for feature in extractor.feature_names:
        zero_ratio = (df[feature] == 0).sum() / len(df)
        if zero_ratio > 0.5:  # 超过50%是0
            zero_features.append((feature, zero_ratio))
            print(f"{feature}: {zero_ratio:.1%} 为零")
    
    if zero_features:
        print(f"\n警告: 发现 {len(zero_features)} 个特征超过50%为零值")
    
    # 保存数据样本
    print("\n" + "=" * 80)
    print("数据样本 (前5场比赛)")
    print("=" * 80)
    sample_cols = ['match_id', 'home_team_id', 'away_team_id', 'label'] + extractor.feature_names[:5]
    print(df[sample_cols].head())
    
    # 保存完整数据用于分析
    output_file = "training_data_debug.csv"
    df.to_csv(output_file, index=False)
    print(f"\n完整数据已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

