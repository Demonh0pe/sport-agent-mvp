"""
测试 Agent 修复效果

验证三个关键场景：
1. 英超积分第六是谁
2. 布赖顿和阿森纳哪个强
3. 诺丁汉森林排第几
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.supervisor.supervisor_agent import SupervisorAgent
from src.shared.llm_client_v2 import get_llm_client


async def test_scenario(supervisor: SupervisorAgent, query: str, scenario_name: str):
    """测试单个场景"""
    print(f"\n{'='*80}")
    print(f"场景：{scenario_name}")
    print(f"问题：{query}")
    print(f"{'='*80}\n")
    
    try:
        result = await supervisor.arun(query)
        
        print(f"状态：{result.get('status', 'unknown')}")
        print(f"\n回答：")
        print(result.get('output', '无输出'))
        
        # 检查是否有错误
        if result.get('status') == 'error':
            print(f"\n⚠️ 错误：{result.get('error', '未知错误')}")
            return False
        else:
            print("\n✅ 测试通过")
            return True
            
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("初始化 Supervisor Agent...")
    
    # 获取 LLM 客户端
    llm_client = get_llm_client()
    
    # 创建 Supervisor
    supervisor = SupervisorAgent(
        llm_client=llm_client,
        enable_memory=False  # 测试时不启用记忆
    )
    
    # 测试场景
    test_cases = [
        ("英超积分第六是谁？", "场景1：查询积分榜特定排名"),
        ("布赖顿和阿森纳哪个强？", "场景2：对比两队实力"),
        ("诺丁汉森林在英超排第几？", "场景3：查询球队排名"),
        ("曼联在英超排第几？", "场景4：查询球队排名（曼联）"),
    ]
    
    results = []
    for query, scenario_name in test_cases:
        success = await test_scenario(supervisor, query, scenario_name)
        results.append((scenario_name, success))
    
    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for scenario_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {scenario_name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！修复成功！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，需要进一步调试")


if __name__ == "__main__":
    asyncio.run(main())

