"""通用 LLM 客户端：负责与大模型 API 进行通信。"""
from __future__ import annotations

import httpx
from openai import AsyncOpenAI
from loguru import logger

from src.shared.config import get_settings

# 获取全局配置
settings = get_settings()

class LLMClient:
    def __init__(self):
        self.config = settings.service.agent.llm
        
        # 初始化 OpenAI 客户端 (兼容 DeepSeek)
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            # 使用 httpx 客户端并设置超时
            http_client=httpx.AsyncClient(timeout=30.0)
        )

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM 生成文本。"""
        try:
            logger.info(f"Calling LLM [{self.config.model}]...")
            
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.temperature,
            )
            
            content = response.choices[0].message.content
            logger.info("LLM Response received.")
            return content

        except Exception as e:
            logger.error(f"LLM Call Failed: {str(e)}")
            return f"[系统降级] AI 服务暂时不可用。（错误信息：{str(e)}）"

llm_client = LLMClient()