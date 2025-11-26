"""
测试LLM客户端的模型切换能力

演示：
1. 自动选择后端
2. 手动切换模型
3. 临时使用不同模型
4. 查看可用模型
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.llm_client_v2 import UnifiedLLMClient, LLMBackend


async def test_auto_backend():
    """测试1: 自动选择后端"""
    print("\n" + "=" * 60)
    print("测试1: 自动选择后端")
    print("=" * 60)

    client = UnifiedLLMClient()
    print(f"✅ 自动选择的后端: {client.backend.value}")
    print(f"✅ 默认模型: {client.default_model}")

    # 测试生成
    response = await client.generate(
        system_prompt="你是一个足球分析助手。",
        user_prompt="简单介绍一下英超联赛。（控制在50字内）"
    )

    print(f"\n📝 生成结果:\n{response}")


async def test_switch_models():
    """测试2: 切换不同模型"""
    print("\n" + "=" * 60)
    print("测试2: 切换不同模型")
    print("=" * 60)

    # 如果Ollama可用，测试不同大小的模型
    try:
        import ollama

        # 列出可用模型
        models_info = ollama.list()
        available_models = [m['name'] for m in models_info.get('models', [])]

        print(f"📋 本地可用模型: {available_models}")

        # 测试不同模型
        client = UnifiedLLMClient(backend="ollama")

        for model_name in available_models[:2]:  # 只测试前2个
            print(f"\n🔄 切换到模型: {model_name}")

            response = await client.generate(
                system_prompt="你是足球专家。",
                user_prompt="用一句话评价曼联。",
                model=model_name  # 临时切换
            )

            print(f"   回答: {response}")

    except ImportError:
        print("⚠️  Ollama未安装，跳过本地模型测试")


async def test_backend_switching():
    """测试3: 后端切换"""
    print("\n" + "=" * 60)
    print("测试3: 后端切换")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 方式1: 初始化时指定
    print("\n方式1: 初始化时指定后端")
    client_ollama = UnifiedLLMClient(backend="ollama", model="qwen2.5:7b")
    print(f"   ✅ 创建了Ollama客户端: {client_ollama.default_model}")

    # 方式2: 动态切换
    print("\n方式2: 动态切换后端")
    client.switch_backend("ollama", model="qwen2.5:7b")
    print(f"   ✅ 切换到: {client.backend.value} - {client.default_model}")


async def test_fallback():
    """测试4: 自动降级"""
    print("\n" + "=" * 60)
    print("测试4: 自动降级机制")
    print("=" * 60)

    # 测试Ollama不可用时的降级
    client = UnifiedLLMClient(backend="ollama")

    print("📝 测试场景: Ollama调用失败时会自动降级到API")
    print("   （这需要在实际运行中触发，此处仅说明机制）")
    print("\n   降级策略:")
    print("   1. 优先使用本地Ollama（快速、免费）")
    print("   2. Ollama失败 → 自动降级到DeepSeek API")
    print("   3. API也失败 → 返回友好的错误信息")


async def test_model_listing():
    """测试5: 列出可用模型"""
    print("\n" + "=" * 60)
    print("测试5: 列出可用模型")
    print("=" * 60)

    # Ollama本地模型
    try:
        client_ollama = UnifiedLLMClient(backend="ollama")
        ollama_models = client_ollama.get_available_models()
        print(f"\n📋 Ollama本地模型:")
        for model in ollama_models:
            print(f"   - {model}")
    except Exception as e:
        print(f"⚠️  Ollama不可用: {e}")

    # DeepSeek API模型
    print(f"\n📋 DeepSeek API模型:")
    print(f"   - deepseek-chat")
    print(f"   - deepseek-coder")

    # OpenAI API模型
    print(f"\n📋 OpenAI API模型:")
    print(f"   - gpt-4o")
    print(f"   - gpt-4o-mini")
    print(f"   - gpt-3.5-turbo")


async def test_configurations():
    """测试6: 不同配置方式"""
    print("\n" + "=" * 60)
    print("测试6: 多种配置方式")
    print("=" * 60)

    # 方式1: 环境变量
    print("\n方式1: 环境变量（最灵活）")
    print("""
    export LLM_BACKEND=ollama
    export LLM_MODEL=qwen2.5:7b
    """)

    # 方式2: 代码指定
    print("\n方式2: 代码指定")
    print("""
    client = UnifiedLLMClient(backend="ollama", model="qwen2.5:14b")
    """)

    # 方式3: 配置文件（未来实现）
    print("\n方式3: 配置文件（推荐用于生产）")
    print("""
    # config/llm.yaml
    backend: ollama
    model: qwen2.5:7b
    fallback_backend: deepseek
    """)


async def main():
    """运行所有测试"""
    print("\n🚀 LLM客户端模型切换能力测试")
    print("=" * 60)

    try:
        await test_auto_backend()
    except Exception as e:
        print(f"❌ 测试1失败: {e}")

    try:
        await test_switch_models()
    except Exception as e:
        print(f"⚠️  测试2跳过: {e}")

    try:
        await test_backend_switching()
    except Exception as e:
        print(f"❌ 测试3失败: {e}")

    try:
        await test_fallback()
    except Exception as e:
        print(f"❌ 测试4失败: {e}")

    try:
        await test_model_listing()
    except Exception as e:
        print(f"❌ 测试5失败: {e}")

    try:
        await test_configurations()
    except Exception as e:
        print(f"❌ 测试6失败: {e}")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
