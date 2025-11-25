"""
快速测试预测功能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.tools.prediction_tool import prediction_tool


async def main():
    print("开始测试预测功能...")
    print("=" * 80)
    
    # 测试1: 曼联 vs 利物浦
    print("\n测试1: 曼联 vs 利物浦")
    print("-" * 80)
    try:
        result = await prediction_tool.predict_match(
            "Manchester United",
            "Liverpool",
            "英超"
        )
        print(result)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())

