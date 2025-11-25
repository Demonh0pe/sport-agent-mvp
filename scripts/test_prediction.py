"""
测试预测功能
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.tools.prediction_tool import prediction_tool


async def main():
    print("=" * 80)
    print("测试比赛预测功能")
    print("=" * 80)
    
    # 测试用例
    test_cases = [
        ("Manchester United", "Liverpool", "英超"),
        ("Bayern München", "Borussia Dortmund", "德甲"),
        ("Real Madrid", "Barcelona", "西甲"),
    ]
    
    for i, (home, away, league) in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}/{len(test_cases)}: {home} vs {away}")
        print(f"{'='*80}\n")
        
        result = await prediction_tool.predict_match(home, away, league)
        print(result)
    
    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
    
    # 提示
    if not prediction_tool.use_ml_model:
        print("\n提示: 当前使用基于规则的预测器")
        print("运行以下命令训练机器学习模型以提升准确率:")
        print("  python src/ml/training/train_baseline.py")


if __name__ == "__main__":
    asyncio.run(main())

