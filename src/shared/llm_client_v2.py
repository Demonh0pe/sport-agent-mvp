"""
LLM客户端 v2 - 支持多种提供商（可扩展设计）

支持的提供商：
- OpenAI
- DeepSeek
- Ollama (本地)
- LM Studio (本地)
- vLLM (本地)
- 更多... (易于扩展)

设计原则：
1. 统一接口
2. 易于扩展
3. 配置驱动
4. 错误处理完善
"""

from openai import AsyncOpenAI
from typing import Optional, Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM客户端（支持多种提供商）
    
    使用OpenAI兼容的接口，支持：
    - OpenAI
    - DeepSeek
    - Ollama (本地)
    - LM Studio (本地)
    - vLLM (本地)
    
    可扩展性设计：
    - 通过环境变量配置
    - 统一的generate接口
    - 自动切换提供商
    """
    
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen:7b",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """
        初始化LLM客户端
        
        Args:
            provider: 提供商（openai/deepseek/ollama/lmstudio/vllm）
            model: 模型名称
            api_key: API密钥（本地模型不需要）
            base_url: 基础URL
            temperature: 温度参数
            max_tokens: 最大token数
        """
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 配置客户端
        self.client = self._init_client(provider, api_key, base_url)
        
        logger.info(f"LLM客户端初始化: {provider} ({model})")
    
    def _init_client(
        self, 
        provider: str, 
        api_key: Optional[str], 
        base_url: Optional[str]
    ) -> AsyncOpenAI:
        """
        初始化OpenAI兼容的客户端
        
        根据提供商配置不同的端点
        """
        if provider in ["ollama", "lmstudio", "vllm"]:
            # 本地大模型（OpenAI兼容）
            default_urls = {
                "ollama": "http://localhost:11434/v1",
                "lmstudio": "http://localhost:1234/v1",
                "vllm": "http://localhost:8000/v1",
            }
            
            url = base_url or default_urls.get(provider)
            
            return AsyncOpenAI(
                base_url=url,
                api_key="local-llm",  # 本地模型不需要真实key
                http_client=httpx.AsyncClient(timeout=120.0)  # 本地模型可能较慢
            )
        
        elif provider == "deepseek":
            # DeepSeek
            return AsyncOpenAI(
                api_key=api_key or "dummy-key",
                base_url=base_url or "https://api.deepseek.com",
                http_client=httpx.AsyncClient(timeout=30.0)
            )
        
        elif provider == "openai":
            # OpenAI
            return AsyncOpenAI(
                api_key=api_key or "dummy-key",
                base_url=base_url,  # None使用默认
                http_client=httpx.AsyncClient(timeout=30.0)
            )
        
        else:
            # 未知提供商，尝试通用配置
            logger.warning(f"未知的LLM提供商: {provider}，尝试通用配置")
            return AsyncOpenAI(
                api_key=api_key or "dummy-key",
                base_url=base_url,
                http_client=httpx.AsyncClient(timeout=30.0)
            )
    
    async def generate(
        self, 
        prompt: str, 
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示词
            system: 系统提示词（可选）
            **kwargs: 额外参数（temperature, max_tokens等）
            
        Returns:
            生成的文本
        """
        try:
            messages = []
            
            # 添加系统提示词
            if system:
                messages.append({"role": "system", "content": system})
            
            # 添加用户提示词
            messages.append({"role": "user", "content": prompt})
            
            # 调用LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            
            result = response.choices[0].message.content
            
            logger.debug(f"LLM生成成功 ({self.provider}): {len(result)} chars")
            
            return result
        
        except Exception as e:
            logger.error(f"LLM生成失败 ({self.provider}): {e}")
            raise
    
    async def batch_generate(
        self, 
        prompts: list[str], 
        **kwargs
    ) -> list[str]:
        """
        批量生成（并发）
        
        Args:
            prompts: 提示词列表
            **kwargs: 额外参数
            
        Returns:
            生成结果列表
        """
        import asyncio
        
        tasks = [self.generate(prompt, **kwargs) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        outputs = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量生成失败: {result}")
                outputs.append("")
            else:
                outputs.append(result)
        
        return outputs
    
    def get_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


# 从环境变量创建默认客户端
def create_default_client() -> LLMClient:
    """
    从环境变量创建默认LLM客户端
    
    环境变量:
    - LLM_PROVIDER: 提供商（默认: ollama）
    - LLM_MODEL: 模型名称
    - LLM_API_KEY: API密钥
    - LLM_BASE_URL: 基础URL
    """
    import os
    
    provider = os.getenv("LLM_PROVIDER", "ollama")
    model = os.getenv("LLM_MODEL", "qwen:7b")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    
    return LLMClient(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )


# 全局单例（向后兼容）
try:
    llm_client = create_default_client()
    logger.info(f"LLM客户端已初始化: {llm_client.get_info()}")
except Exception as e:
    logger.warning(f"LLM客户端初始化失败: {e}")
    # 创建一个虚拟客户端
    llm_client = LLMClient(provider="ollama", model="dummy")


# 测试代码
if __name__ == "__main__":
    import asyncio
    import sys
    from pathlib import Path
    
    # 添加项目根目录
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    async def test():
        print("=" * 80)
        print("LLM客户端测试")
        print("=" * 80)
        
        # 测试不同提供商
        providers_to_test = [
            ("ollama", "qwen:7b", None, "http://localhost:11434/v1"),
            # ("deepseek", "deepseek-chat", "your-api-key", None),
            # ("openai", "gpt-3.5-turbo", "your-api-key", None),
        ]
        
        for provider, model, api_key, base_url in providers_to_test:
            print(f"\n测试: {provider} ({model})")
            print("-" * 80)
            
            try:
                client = LLMClient(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                )
                
                # 测试生成
                prompt = "请用一句话介绍曼联足球俱乐部"
                response = await client.generate(prompt)
                
                print(f"✅ 成功")
                print(f"响应: {response[:100]}...")
                
            except Exception as e:
                print(f"❌ 失败: {e}")
        
        print("\n" + "=" * 80)
    
    asyncio.run(test())
