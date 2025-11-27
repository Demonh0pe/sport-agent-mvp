#!/usr/bin/env python3
"""
快速测试修复后的Agent系统
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.agent_service_v3 import agent_service_v3


async def main():
    """测试修复后的Agent"""
    
    print("=" * 80)
    print("测试修复后的Agent系统")
    print("=" * 80)
    print()
    
    # 测试用例
    test_queries = [
        "英超最后一名是谁",
        "曼联最近5场比赛战绩如何",
        "英超积分榜前3名是谁",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}/{len(test_queries)}: {query}")
        print('='*80)
        
        try:
            result = await agent_service_v3.chat(query)
            
            print(f"\n✅ 成功")
            print(f"\n答案:\n{result['answer']}")
            print(f"\n使用工具: {result['tools_used']}")
            print(f"耗时: {result['duration_seconds']:.2f}秒")
            
        except Exception as e:
            print(f"\n❌ 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("测试完成")
    print('='*80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试中断")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

