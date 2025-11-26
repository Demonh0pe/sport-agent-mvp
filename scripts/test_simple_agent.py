"""
测试SimpleAgent - 三个核心模块

测试场景：
1. 赛事查询：战绩、排名
2. 赛事分析：状态分析、对比、预测
3. 赛事总结：简洁摘要
"""
import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent.simple_agent import SimpleAgent


# 测试用例
TEST_CASES = [
    # 查询类
    {
        "category": "查询",
        "query": "曼联最近5场比赛战绩",
        "expected_intent": "query"
    },
    {
        "category": "查询",
        "query": "利物浦在英超排名第几",
        "expected_intent": "query"
    },
    {
        "category": "查询",
        "query": "曼联对利物浦的历史交锋",
        "expected_intent": "query"
    },

    # 分析类
    {
        "category": "分析",
        "query": "分析一下曼联最近的状态",
        "expected_intent": "analysis"
    },
    {
        "category": "分析",
        "query": "曼联和利物浦谁更强？",
        "expected_intent": "analysis"
    },
    {
        "category": "分析",
        "query": "预测曼联对利物浦谁会赢",
        "expected_intent": "analysis"
    },

    # 总结类
    {
        "category": "总结",
        "query": "总结曼联最近的情况",
        "expected_intent": "summary"
    },
    {
        "category": "总结",
        "query": "简要说明利物浦的状态",
        "expected_intent": "summary"
    },
]


async def test_single_query(agent: SimpleAgent, test_case: dict, index: int):
    """测试单个查询"""
    print(f"\n{'=' * 80}")
    print(f"测试 {index + 1}: {test_case['category']} - {test_case['query']}")
    print(f"{'=' * 80}")

    start_time = datetime.now()

    try:
        response = await agent.chat(test_case['query'])

        # 计算耗时
        elapsed = (datetime.now() - start_time).total_seconds()

        # 打印结果
        print(f"\n✅ 成功")
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"🎯 意图: {response.intent} (期望: {test_case['expected_intent']})")
        print(f"📦 实体: {response.entities}")
        print(f"🔧 模块: {response.module_used}")
        print(f"\n📝 回答:")
        print(f"{'-' * 80}")
        print(response.answer)
        print(f"{'-' * 80}")

        # 验证意图
        if response.intent == test_case['expected_intent']:
            print(f"✅ 意图识别正确")
        else:
            print(f"⚠️  意图识别有误（期望: {test_case['expected_intent']}, 实际: {response.intent}）")

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ 失败")
        print(f"⏱️  耗时: {elapsed:.2f}秒")
        print(f"❌ 错误: {str(e)}")


async def test_all():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 SimpleAgent 测试开始")
    print("=" * 80)

    # 初始化Agent
    agent = SimpleAgent()

    # 统计
    total = len(TEST_CASES)
    success = 0
    failed = 0

    # 逐个测试
    for i, test_case in enumerate(TEST_CASES):
        try:
            await test_single_query(agent, test_case, i)
            success += 1
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            failed += 1

        # 间隔（避免API限流）
        if i < total - 1:
            print(f"\n⏸️  等待1秒...")
            await asyncio.sleep(1)

    # 打印总结
    print(f"\n{'=' * 80}")
    print(f"📊 测试总结")
    print(f"{'=' * 80}")
    print(f"总计: {total}")
    print(f"✅ 成功: {success}")
    print(f"❌ 失败: {failed}")
    print(f"成功率: {success / total * 100:.1f}%")
    print(f"{'=' * 80}\n")


async def interactive_mode():
    """交互模式"""
    print("\n" + "=" * 80)
    print("💬 SimpleAgent 交互模式")
    print("=" * 80)
    print("输入 'quit' 或 'exit' 退出\n")

    agent = SimpleAgent()

    while True:
        try:
            # 获取用户输入
            user_input = input("👤 你: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break

            # 调用Agent
            start_time = datetime.now()
            response = await agent.chat(user_input)
            elapsed = (datetime.now() - start_time).total_seconds()

            # 打印结果
            print(f"\n🤖 Agent: \n{response.answer}\n")
            print(f"💡 (意图: {response.intent}, 模块: {response.module_used}, 耗时: {elapsed:.2f}s)\n")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")


async def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # 交互模式
        await interactive_mode()
    else:
        # 测试模式
        await test_all()


if __name__ == "__main__":
    asyncio.run(main())
