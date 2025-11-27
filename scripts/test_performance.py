#!/usr/bin/env python3
"""
性能测试脚本 - 对比不同配置的速度和质量

用法：
    python scripts/test_performance.py
"""

import asyncio
import time
import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.agent_service_v3 import ask


async def test_query(query: str, model_name: str) -> dict:
    """测试单个查询"""
    print(f"\n{'='*60}")
    print(f"模型: {model_name}")
    print(f"问题: {query}")
    print(f"{'='*60}")
    
    start = time.time()
    
    try:
        answer = await ask(query)
        duration = time.time() - start
        
        print(f"\n回答: {answer[:200]}...")
        print(f"\n耗时: {duration:.2f}秒")
        print(f"回答长度: {len(answer)} 字符")
        
        return {
            "model": model_name,
            "query": query,
            "duration": duration,
            "answer_length": len(answer),
            "status": "success"
        }
    
    except Exception as e:
        duration = time.time() - start
        print(f"\n错误: {e}")
        print(f"耗时: {duration:.2f}秒")
        
        return {
            "model": model_name,
            "query": query,
            "duration": duration,
            "status": "error",
            "error": str(e)
        }


async def main():
    """主测试流程"""
    
    print("""
╔══════════════════════════════════════════════════════════╗
║           Sport Agent V3 性能测试                        ║
╚══════════════════════════════════════════════════════════╝

说明：
  - 会使用当前配置的 LLM 模型进行测试
  - 请确保已设置 LLM_MODEL 环境变量
  - 测试 3 个不同类型的查询
  - 最后显示性能统计

当前配置：
""")
    
    import os
    print(f"  LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'ollama')}")
    print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'qwen2.5:7b')}")
    print()
    
    model_name = os.getenv('LLM_MODEL', 'unknown')
    
    # 测试问题集
    test_queries = [
        "曼联最近5场比赛战绩如何？",           # 简单查询
        "阿森纳对曼城谁会赢？",                 # 预测分析
        "曼联和利物浦对比，谁更强？为什么？",   # 复杂分析
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n\n[{i}/{len(test_queries)}] 测试中...")
        result = await test_query(query, model_name)
        results.append(result)
        
        # 短暂休息
        await asyncio.sleep(1)
    
    # 统计结果
    print(f"\n\n{'='*60}")
    print("性能统计")
    print(f"{'='*60}")
    
    total_time = sum(r['duration'] for r in results)
    success_count = sum(1 for r in results if r['status'] == 'success')
    
    print(f"\n模型: {model_name}")
    print(f"总查询数: {len(results)}")
    print(f"成功数: {success_count}")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"平均耗时: {total_time/len(results):.2f}秒")
    
    print(f"\n详细结果:")
    print(f"{'类型':<10} {'耗时':<10} {'回答长度':<10}")
    print(f"{'-'*30}")
    
    query_types = ["简单查询", "预测分析", "复杂分析"]
    for result, qtype in zip(results, query_types):
        if result['status'] == 'success':
            print(f"{qtype:<10} {result['duration']:>6.2f}秒   {result['answer_length']:>6}字")
        else:
            print(f"{qtype:<10} {'失败':<10}")
    
    print(f"\n{'='*60}")
    print("建议：")
    
    avg_time = total_time / len(results)
    if avg_time > 15:
        print("  - 当前速度较慢，建议：")
        print("    1. 切换到 qwen2.5:3b（速度提升2-3倍）")
        print("    2. 或使用 DeepSeek API（速度提升5-8倍）")
    elif avg_time > 8:
        print("  - 当前速度中等，可以考虑：")
        print("    1. 使用 DeepSeek API 进一步提升")
        print("    2. 或优化数据库查询")
    else:
        print("  - 当前速度良好！")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试已中断")
    except Exception as e:
        print(f"\n\n测试失败：{e}")
        import traceback
        traceback.print_exc()

