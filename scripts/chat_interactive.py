#!/usr/bin/env python3
"""
交互式聊天脚本 - Sport Agent V3

用法：
    python scripts/chat_interactive.py

功能：
    - 交互式对话测试
    - 支持连续提问
    - 显示详细响应
    - 支持退出命令
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.agent_service_v3 import ask


async def main():
    """交互式聊天主循环"""
    
    print("=" * 60)
    print("Sport Agent V3 交互式测试")
    print("=" * 60)
    print()
    print("提示：")
    print("  - 输入你的问题进行测试")
    print("  - 输入 'exit' 或 'quit' 退出")
    print("  - 输入 'clear' 清屏")
    print()
    print("示例问题：")
    print("  - 曼联最近5场比赛战绩如何？")
    print("  - 阿森纳对曼城谁会赢？")
    print("  - 曼联和利物浦谁更强？为什么？")
    print("  - 英超积分榜前5是谁？")
    print()
    print("=" * 60)
    print()
    
    session_count = 0
    
    while True:
        try:
            # 获取用户输入
            query = input("\n你: ").strip()
            
            # 检查退出命令
            if query.lower() in ['exit', 'quit', 'q', '退出']:
                print("\n再见！")
                break
            
            # 检查清屏命令
            if query.lower() in ['clear', 'cls', '清屏']:
                import os
                os.system('clear' if sys.platform != 'win32' else 'cls')
                print("Sport Agent V3 交互式测试")
                print("=" * 60)
                continue
            
            # 跳过空输入
            if not query:
                continue
            
            session_count += 1
            
            print(f"\nAgent: 正在处理...")
            print("-" * 60)
            
            # 调用 Agent
            try:
                answer = await ask(query)
                
                print(f"\n{answer}")
                print("-" * 60)
                print(f"[会话 {session_count} 完成]")
                
            except Exception as e:
                print(f"\n错误：{e}")
                print("-" * 60)
                print(f"[会话 {session_count} 失败]")
        
        except KeyboardInterrupt:
            print("\n\n收到中断信号，退出...")
            break
        
        except EOFError:
            print("\n\n输入结束，退出...")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"\n程序异常：{e}")
        sys.exit(1)

