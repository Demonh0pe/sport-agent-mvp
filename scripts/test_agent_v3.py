"""
测试 Agent Service V3 新架构

运行方式：
python -m scripts.test_agent_v3
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.agent_service_v3 import agent_service_v3, ask, ask_expert


async def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试 Agent Service V3 新架构")
    print("=" * 60)
    
    # 测试1: 列出可用专家
    print("\n1. 可用的专家：")
    experts = agent_service_v3.list_available_experts()
    print(f"   {experts}")
    
    # 测试2: 数据查询（DataStatsAgent）
    print("\n2. 测试数据查询专家（DataStatsAgent）")
    print("   问题：曼联最近5场比赛战绩如何？")
    try:
        result = await ask_expert("data_stats", "曼联最近5场比赛战绩如何？")
        print(f"   回答：{result[:200]}..." if len(result) > 200 else f"   回答：{result}")
    except Exception as e:
        print(f"   错误：{e}")
    
    # 测试3: 预测（PredictionAgent）
    print("\n3. 测试预测专家（PredictionAgent）")
    print("   问题：阿森纳对曼城谁会赢？")
    try:
        result = await ask_expert("prediction", "阿森纳对曼城谁会赢？")
        print(f"   回答：{result[:300]}..." if len(result) > 300 else f"   回答：{result}")
    except Exception as e:
        print(f"   错误：{e}")
    
    # 测试4: 通过 Supervisor 提问
    print("\n4. 测试 Supervisor Agent（综合调度）")
    print("   问题：曼联和利物浦谁更强？为什么？")
    try:
        response = await agent_service_v3.chat(
            query="曼联和利物浦谁更强？为什么？",
            session_id="test_session_1"
        )
        print(f"   使用的工具：{response['tools_used']}")
        print(f"   回答：{response['answer'][:400]}..." if len(response['answer']) > 400 else f"   回答：{response['answer']}")
        print(f"   耗时：{response['duration_seconds']:.2f}秒")
    except Exception as e:
        print(f"   错误：{e}")
    
    # 测试5: 便捷接口
    print("\n5. 测试便捷接口（ask）")
    print("   问题：英超积分榜前5是谁？")
    try:
        answer = await ask("英超积分榜前5是谁？")
        print(f"   回答：{answer[:200]}..." if len(answer) > 200 else f"   回答：{answer}")
    except Exception as e:
        print(f"   错误：{e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())

