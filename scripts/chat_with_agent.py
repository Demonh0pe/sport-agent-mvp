"""
交互式Agent问答界面
支持实时对话，查看工具调用详情
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.getcwd())

from src.services.api.services.agent_v2 import agent_service
from loguru import logger

# 配置logger只显示错误
logger.remove()
logger.add(sys.stderr, level="ERROR")


def print_header():
    """打印欢迎界面"""
    print("\n" + "=" * 80)
    print("🤖 Sport Agent MVP - 交互式问答系统")
    print("=" * 80)
    print("\n💡 使用说明:")
    print("   - 输入你的问题，按回车提交")
    print("   - 输入 'exit' 或 'quit' 或 'q' 退出")
    print("   - 输入 'clear' 清屏")
    print("   - 输入 'help' 查看示例问题")
    print("\n🎯 示例问题:")
    print("   • 曼联最近5场比赛的战绩如何？")
    print("   • 预测一下曼城和阿森纳的比赛")
    print("   • 利物浦在英超中处于什么地位？")
    print("   • 皇马对巴萨，谁会赢？")
    print("\n" + "=" * 80 + "\n")


def print_help():
    """打印帮助信息"""
    print("\n" + "=" * 80)
    print("📚 示例问题")
    print("=" * 80)
    print("\n【比赛预测】")
    print("   • 曼联对利物浦，谁会赢？")
    print("   • 预测一下拜仁和多特的比赛")
    print("   • 皇马vs巴萨，哪个队会获胜")
    print("\n【战绩查询】")
    print("   • 曼联最近5场比赛的战绩如何")
    print("   • 利物浦近期表现怎么样")
    print("   • 阿森纳最近胜率如何")
    print("\n【排名查询】")
    print("   • 利物浦在英超中处于什么地位")
    print("   • 曼城现在排名第几")
    print("\n【对战分析】")
    print("   • 曼联和切尔西历史交锋记录")
    print("   • 皇马对巴萨的往绩如何")
    print("\n" + "=" * 80 + "\n")


def format_answer(response):
    """格式化Agent的回答"""
    print("\n" + "─" * 80)
    print("🤖 Agent回答:")
    print("─" * 80)
    print(response.answer)
    print()


def format_execution_details(response):
    """格式化执行详情"""
    if not response.execution_steps:
        return
    
    print("📊 执行详情:")
    print(f"   ⏱️  总耗时: {response.total_execution_time_ms}ms")
    print(f"   🔧 工具调用: {len(response.execution_steps)} 个")
    print()
    
    for i, step in enumerate(response.execution_steps, 1):
        status_icon = "✅" if step.status == "success" else "❌"
        print(f"   {i}. {status_icon} {step.tool_name}")
        print(f"      ⏱️  耗时: {step.execution_time_ms}ms")
        
        # 截取输出的前100个字符
        if step.output and len(str(step.output)) > 100:
            output_preview = str(step.output)[:100] + "..."
        else:
            output_preview = str(step.output) if step.output else "(无输出)"
        
        print(f"      📤 输出: {output_preview}")
        print()


async def process_query(query: str):
    """处理用户查询"""
    try:
        # 显示处理提示
        print("\n⏳ 正在思考...", end="", flush=True)
        
        start_time = datetime.now()
        response = await agent_service.process_query(query)
        end_time = datetime.now()
        
        # 清除"正在思考"提示
        print("\r" + " " * 20 + "\r", end="")
        
        # 显示回答
        format_answer(response)
        
        # 显示执行详情
        format_execution_details(response)
        
        # 显示总耗时
        total_time = (end_time - start_time).total_seconds()
        print(f"⏱️  总响应时间: {total_time:.2f}秒")
        print("─" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  查询被中断")
        raise
    except Exception as e:
        print("\n\n❌ 查询失败:")
        print(f"   错误: {str(e)}")
        print("   请检查日志获取详细信息\n")


async def main():
    """主函数"""
    print_header()
    
    while True:
        try:
            # 获取用户输入
            query = input("💬 你的问题: ").strip()
            
            # 处理命令
            if not query:
                continue
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 再见！感谢使用Sport Agent MVP\n")
                break
            
            if query.lower() == 'clear':
                os.system('clear' if os.name != 'nt' else 'cls')
                print_header()
                continue
            
            if query.lower() == 'help':
                print_help()
                continue
            
            # 处理查询
            await process_query(query)
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！感谢使用Sport Agent MVP\n")
            break
        except EOFError:
            print("\n\n👋 再见！感谢使用Sport Agent MVP\n")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}\n")
            continue


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 再见！")

