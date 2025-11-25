"""
简化版交互式问答 - 只显示关键信息
"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from src.services.api.dependencies import get_agent_service_v2
from src.services.api.schemas.agent import AgentQuery
from loguru import logger

# 禁用日志输出
logger.remove()
logger.add(sys.stderr, level="ERROR")

# 获取 Agent 服务实例
agent_service = get_agent_service_v2()


async def chat():
    """简单的聊天循环"""
    print("\n" + "=" * 60)
    print("🤖 Sport Agent - 简洁对话模式")
    print("=" * 60)
    print("输入问题开始对话，输入 'exit' 退出")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # 获取输入
            query = input("❓ 你: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 再见!\n")
                break
            
            # 处理查询
            print("🤖 Agent: ", end="", flush=True)
            query_obj = AgentQuery(query=query)
            response = await agent_service.run_query(query_obj)
            print(response.answer)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 再见!\n")
            break
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(chat())

