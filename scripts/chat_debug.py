"""
调试版交互式问答 - 显示完整工具调用信息
"""
import asyncio
import sys
import os
import json

sys.path.append(os.getcwd())

from src.services.api.services.agent_v2 import agent_service
from loguru import logger

# 配置logger显示详细日志
logger.remove()
logger.add(sys.stderr, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


async def chat_debug():
    """调试模式聊天"""
    print("\n" + "=" * 80)
    print("🔧 Sport Agent - 调试模式")
    print("=" * 80)
    print("显示所有工具调用、参数和输出")
    print("输入 'exit' 退出")
    print("=" * 80 + "\n")
    
    while True:
        try:
            query = input("\n💬 问题: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 退出\n")
                break
            
            print("\n" + "=" * 80)
            print("🔍 开始处理查询")
            print("=" * 80)
            
            response = await agent_service.process_query(query)
            
            print("\n" + "=" * 80)
            print("📋 执行计划")
            print("=" * 80)
            if hasattr(response, 'plan_steps') and response.plan_steps:
                for i, step in enumerate(response.plan_steps, 1):
                    print(f"{i}. {step}")
            print()
            
            print("=" * 80)
            print("🔧 工具执行详情")
            print("=" * 80)
            for i, step in enumerate(response.execution_steps, 1):
                print(f"\n[工具 {i}] {step.tool_name}")
                print(f"状态: {step.status}")
                print(f"耗时: {step.execution_time_ms}ms")
                
                if step.input_params:
                    print(f"输入参数:")
                    print(json.dumps(step.input_params, indent=2, ensure_ascii=False))
                
                if step.output:
                    print(f"输出:")
                    output_str = str(step.output)
                    if len(output_str) > 500:
                        print(output_str[:500] + "...")
                    else:
                        print(output_str)
                
                if step.error:
                    print(f"❌ 错误: {step.error}")
                
                print("-" * 80)
            
            print("\n" + "=" * 80)
            print("💬 最终回答")
            print("=" * 80)
            print(response.answer)
            print()
            
            print("=" * 80)
            print(f"⏱️  总耗时: {response.total_execution_time_ms}ms")
            print("=" * 80 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 退出\n")
            break
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(chat_debug())

