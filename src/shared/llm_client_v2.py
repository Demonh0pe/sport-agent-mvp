"""
灵活的LLM客户端 - 支持多种后端

支持的后端：
1. Ollama（本地模型） - 优先级最高
2. DeepSeek API
3. OpenAI API
4. Claude API（未来扩展）

特性：
- 自动降级（Ollama不可用 → API）
- 配置灵活（环境变量、配置文件、代码）
- 统一接口（无需修改调用代码）
"""
from __future__ import annotations

import os
import httpx
from typing import Optional, Dict, Any
from enum import Enum
from loguru import logger

# 尝试导入各种后端
try:
    from ollama import AsyncClient as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not installed. Run: pip install ollama")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LLMBackend(Enum):
    """LLM后端类型"""
    OLLAMA = "ollama"          # 本地模型
    DEEPSEEK = "deepseek"      # DeepSeek API
    OPENAI = "openai"          # OpenAI API
    CLAUDE = "claude"          # Claude API（未来）


class UnifiedLLMClient:
    """
    统一的LLM客户端

    使用示例：
        # 1. 自动选择后端（推荐）
        client = UnifiedLLMClient()
        response = await client.generate("system", "user")

        # 2. 指定后端
        client = UnifiedLLMClient(backend="ollama")

        # 3. 指定模型
        client = UnifiedLLMClient(backend="ollama", model="qwen2.5:14b")

        # 4. 临时切换模型
        response = await client.generate("sys", "user", model="qwen2.5:3b")
    """

    def __init__(
        self,
        backend: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        初始化LLM客户端

        Args:
            backend: 指定后端（不指定则自动选择）
            model: 指定模型（不指定则使用默认）
            **kwargs: 其他配置参数
        """
        self.backend = self._select_backend(backend)
        self.default_model = self._get_default_model(model)
        self.config = kwargs

        # 初始化对应的客户端
        self._init_clients()

        logger.info(f"[LLMClient] Using backend: {self.backend.value}, model: {self.default_model}")

    def _select_backend(self, backend: Optional[str]) -> LLMBackend:
        """
        选择后端

        优先级：
        1. 用户指定
        2. 环境变量 LLM_BACKEND
        3. 自动检测（Ollama > DeepSeek）
        """
        # 1. 用户指定
        if backend:
            return LLMBackend(backend)

        # 2. 环境变量
        env_backend = os.getenv("LLM_BACKEND")
        if env_backend:
            return LLMBackend(env_backend)

        # 3. 自动检测
        if OLLAMA_AVAILABLE:
            # 检测Ollama是否运行
            try:
                import ollama
                ollama.list()  # 测试连接
                return LLMBackend.OLLAMA
            except Exception:
                pass

        # 降级到API
        return LLMBackend.DEEPSEEK

    def _get_default_model(self, model: Optional[str]) -> str:
        """获取默认模型"""
        # 1. 用户指定
        if model:
            return model

        # 2. 环境变量
        env_model = os.getenv("LLM_MODEL")
        if env_model:
            return env_model

        # 3. 根据后端选择默认值
        defaults = {
            LLMBackend.OLLAMA: "qwen2.5:7b",
            LLMBackend.DEEPSEEK: "deepseek-chat",
            LLMBackend.OPENAI: "gpt-4o-mini",
        }

        return defaults.get(self.backend, "qwen2.5:7b")

    def _init_clients(self):
        """初始化各后端客户端"""
        if self.backend == LLMBackend.OLLAMA:
            if OLLAMA_AVAILABLE:
                self.ollama_client = OllamaClient()
            else:
                logger.error("Ollama backend selected but not available!")
                raise RuntimeError("Ollama not installed. Run: pip install ollama")

        elif self.backend in [LLMBackend.DEEPSEEK, LLMBackend.OPENAI]:
            if not OPENAI_AVAILABLE:
                raise RuntimeError("OpenAI library not installed. Run: pip install openai")

            api_key = self._get_api_key()
            base_url = self._get_base_url()

            self.api_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=httpx.AsyncClient(timeout=30.0)
            )

    def _get_api_key(self) -> str:
        """获取API密钥"""
        if self.backend == LLMBackend.DEEPSEEK:
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                raise ValueError("DEEPSEEK_API_KEY not set!")
            return key

        elif self.backend == LLMBackend.OPENAI:
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY not set!")
            return key

        return ""

    def _get_base_url(self) -> Optional[str]:
        """获取API base URL"""
        if self.backend == LLMBackend.DEEPSEEK:
            return "https://api.deepseek.com"
        return None

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        生成文本（统一接口）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 临时切换模型（可选）
            temperature: 温度
            max_tokens: 最大tokens
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        use_model = model or self.default_model

        try:
            if self.backend == LLMBackend.OLLAMA:
                return await self._generate_ollama(
                    system_prompt,
                    user_prompt,
                    use_model,
                    temperature,
                    max_tokens
                )
            else:
                return await self._generate_api(
                    system_prompt,
                    user_prompt,
                    use_model,
                    temperature,
                    max_tokens
                )

        except Exception as e:
            logger.error(f"[LLMClient] Generation failed: {e}")

            # 尝试降级
            if self.backend == LLMBackend.OLLAMA:
                logger.warning("[LLMClient] Ollama failed, fallback to DeepSeek API")
                return await self._fallback_to_api(system_prompt, user_prompt)

            # 返回错误信息
            return f"[系统降级] AI服务暂时不可用。（错误：{str(e)}）"

    async def _generate_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Ollama后端生成"""
        logger.info(f"[Ollama] Calling model: {model}")

        response = await self.ollama_client.chat(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            options={
                'temperature': temperature,
                'num_predict': max_tokens
            }
        )

        content = response['message']['content']
        logger.info(f"[Ollama] Response received ({len(content)} chars)")
        return content

    async def _generate_api(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """API后端生成（DeepSeek/OpenAI）"""
        logger.info(f"[{self.backend.value}] Calling model: {model}")

        response = await self.api_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content
        logger.info(f"[{self.backend.value}] Response received")
        return content

    async def _fallback_to_api(self, system_prompt: str, user_prompt: str) -> str:
        """降级到DeepSeek API"""
        try:
            # 临时创建DeepSeek客户端
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                return "[系统降级] 本地模型和API均不可用。"

            fallback_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
                http_client=httpx.AsyncClient(timeout=30.0)
            )

            response = await fallback_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[Fallback] Failed: {e}")
            return "[系统降级] 本地模型和API均不可用。"

    def switch_backend(self, backend: str, model: Optional[str] = None):
        """
        动态切换后端

        Args:
            backend: 新后端
            model: 新模型（可选）
        """
        self.backend = LLMBackend(backend)
        if model:
            self.default_model = model
        self._init_clients()
        logger.info(f"[LLMClient] Switched to {backend}, model: {self.default_model}")

    def get_available_models(self) -> list:
        """
        获取可用的模型列表

        Returns:
            模型名称列表
        """
        if self.backend == LLMBackend.OLLAMA:
            try:
                import ollama
                models = ollama.list()
                return [m['name'] for m in models.get('models', [])]
            except Exception as e:
                logger.error(f"Failed to list Ollama models: {e}")
                return []

        # API后端返回预定义列表
        return {
            LLMBackend.DEEPSEEK: ["deepseek-chat", "deepseek-coder"],
            LLMBackend.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        }.get(self.backend, [])


# 全局单例（自动选择后端）
llm_client = UnifiedLLMClient()


# 便捷函数
async def generate(system_prompt: str, user_prompt: str, **kwargs) -> str:
    """便捷的生成函数"""
    return await llm_client.generate(system_prompt, user_prompt, **kwargs)


def switch_model(backend: str, model: Optional[str] = None):
    """便捷的切换函数"""
    llm_client.switch_backend(backend, model)
