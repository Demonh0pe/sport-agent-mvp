"""
测试Agent预测功能集成
"""
import asyncio
import sys
sys.path.insert(0, '.')

from src.services.api.services.agent_v2 import AgentServiceV2
from src.services.api.schemas.agent import AgentQuery
from src.shared.config import Settings


async def main():
    print("=" * 80)
    print("测试Agent预测功能集成")
    print("=" * 80)
    
    # 初始化Agent
    settings = Settings()
    agent = AgentServiceV2(settings)
    
    # 测试用例
    test_queries = [
        "曼联对利物浦，谁会赢？",
        "预测一下拜仁和多特的比赛",
        "皇马vs巴萨，哪个队会获胜",
        "利物浦在英超中处于什么地位",
        "曼联最近5场比赛的战绩如何",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}/{len(test_queries)}: {query}")
        print(f"{'='*80}\n")
        
        try:
            # 执行查询
            response = await agent.run_query(AgentQuery(query=query))
            
            print(f"回答:\n{response.answer}\n")
            print(f"推理: {response.reasoning}")
            print(f"规划步骤: {response.plan_steps}")
            
            if response.tool_traces:
                print(f"\n工具执行:")
                for trace in response.tool_traces:
                    print(f"  - {trace.tool_name}: {trace.latency_ms}ms")
                    print(f"    输出: {trace.output_snippet[:100]}...")
        
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

