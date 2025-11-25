"""
快速诊断
"""
import asyncio
import sys
sys.path.insert(0, '.')

from src.ml.features.match_features import MatchFeatureExtractor
from datetime import datetime


async def main():
    extractor = MatchFeatureExtractor()
    
    # 测试单场比赛
    print("测试单场比赛特征提取...")
    print("比赛: MUN (曼联) vs LIV (利物浦)")
    
    features = await extractor.extract_features_for_match(
        home_team_id="MUN",
        away_team_id="LIV",
        league_id="EPL",
        match_date=datetime.now(),
        season="2024"
    )
    
    print("\n提取的特征:")
    for key, value in features.items():
        print(f"  {key:30} = {value:.4f}")
    
    # 统计零值
    zero_count = sum(1 for v in features.values() if v == 0)
    total = len(features)
    print(f"\n零值特征: {zero_count}/{total} ({zero_count/total:.1%})")
    
    if zero_count > total * 0.5:
        print("\n警告: 超过50%的特征为零值!")
        print("可能原因:")
        print("1. 积分榜数据缺失")
        print("2. 历史比赛数据不足")
        print("3. 特征提取逻辑有问题")


if __name__ == "__main__":
    asyncio.run(main())

