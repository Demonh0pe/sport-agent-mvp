"""
中英文翻译助手

功能：
1. 智能识别中英文输入
2. 数据库英文数据的中文展示
3. LLM增强的语义理解
4. 缓存常用翻译

设计原则：
- 优先使用预定义映射（快速、准确）
- LLM作为fallback（灵活、智能）
- 缓存结果减少LLM调用
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import re

from src.shared.llm_client_v2 import get_llm_client

llm_client = get_llm_client()

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """翻译结果"""
    original: str
    translated: str
    language: str  # zh/en
    method: str    # predefined/llm/cache
    confidence: float = 1.0


class TranslationHelper:
    """
    中英文翻译助手
    
    工作流程：
    1. 检测输入语言
    2. 查找预定义映射
    3. 使用LLM翻译（fallback）
    4. 缓存结果
    """
    
    def __init__(self):
        self._zh_to_en_cache: Dict[str, str] = {}
        self._en_to_zh_cache: Dict[str, str] = {}
        
        # 预定义的足球术语翻译
        self._predefined_terms = self._load_predefined_terms()
    
    def _load_predefined_terms(self) -> Dict[str, Dict[str, str]]:
        """加载预定义术语"""
        return {
            "zh_to_en": {
                # 球队相关
                "球队": "team",
                "俱乐部": "club",
                "主场": "home",
                "客场": "away",
                
                # 比赛相关
                "比赛": "match",
                "赛事": "fixture",
                "战绩": "record",
                "胜": "win",
                "负": "loss",
                "平": "draw",
                "比分": "score",
                "进球": "goal",
                
                # 联赛相关
                "联赛": "league",
                "积分": "points",
                "排名": "rank",
                "积分榜": "standings",
                
                # 分析相关
                "状态": "form",
                "趋势": "trend",
                "分析": "analysis",
                "预测": "prediction",
                "对比": "comparison",
                
                # 时间相关
                "最近": "recent",
                "近期": "recent",
                "本赛季": "this season",
                "上赛季": "last season",
            },
            "en_to_zh": {
                # 反向映射
                "team": "球队",
                "club": "俱乐部",
                "home": "主场",
                "away": "客场",
                "match": "比赛",
                "fixture": "赛事",
                "record": "战绩",
                "win": "胜",
                "loss": "负",
                "draw": "平",
                "score": "比分",
                "goal": "进球",
                "league": "联赛",
                "points": "积分",
                "rank": "排名",
                "standings": "积分榜",
                "form": "状态",
                "trend": "趋势",
                "analysis": "分析",
                "prediction": "预测",
                "comparison": "对比",
                "recent": "最近",
                "this season": "本赛季",
                "last season": "上赛季",
            }
        }
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Returns:
            "zh" 或 "en"
        """
        # 检查是否包含中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        
        if len(chinese_chars) > len(text) * 0.3:  # 超过30%是中文
            return "zh"
        else:
            return "en"
    
    async def translate_to_chinese(
        self, 
        text: str, 
        context: str = "football"
    ) -> TranslationResult:
        """
        将英文翻译为中文
        
        Args:
            text: 要翻译的文本
            context: 上下文（用于LLM理解）
            
        Returns:
            TranslationResult
        """
        # 1. 检查语言
        lang = self.detect_language(text)
        if lang == "zh":
            return TranslationResult(
                original=text,
                translated=text,
                language="zh",
                method="no_translation_needed"
            )
        
        # 2. 检查缓存
        if text in self._en_to_zh_cache:
            return TranslationResult(
                original=text,
                translated=self._en_to_zh_cache[text],
                language="en",
                method="cache"
            )
        
        # 3. 检查预定义映射
        text_lower = text.lower()
        if text_lower in self._predefined_terms["en_to_zh"]:
            translated = self._predefined_terms["en_to_zh"][text_lower]
            self._en_to_zh_cache[text] = translated
            return TranslationResult(
                original=text,
                translated=translated,
                language="en",
                method="predefined"
            )
        
        # 4. 使用LLM翻译
        try:
            translated = await self._llm_translate(text, "en", "zh", context)
            self._en_to_zh_cache[text] = translated
            return TranslationResult(
                original=text,
                translated=translated,
                language="en",
                method="llm",
                confidence=0.8
            )
        except Exception as e:
            logger.error(f"LLM翻译失败: {e}")
            # Fallback：保持原文
            return TranslationResult(
                original=text,
                translated=text,
                language="en",
                method="fallback",
                confidence=0.0
            )
    
    async def translate_to_english(
        self, 
        text: str, 
        context: str = "football"
    ) -> TranslationResult:
        """将中文翻译为英文"""
        # 类似的逻辑
        lang = self.detect_language(text)
        if lang == "en":
            return TranslationResult(
                original=text,
                translated=text,
                language="en",
                method="no_translation_needed"
            )
        
        if text in self._zh_to_en_cache:
            return TranslationResult(
                original=text,
                translated=self._zh_to_en_cache[text],
                language="zh",
                method="cache"
            )
        
        if text in self._predefined_terms["zh_to_en"]:
            translated = self._predefined_terms["zh_to_en"][text]
            self._zh_to_en_cache[text] = translated
            return TranslationResult(
                original=text,
                translated=translated,
                language="zh",
                method="predefined"
            )
        
        try:
            translated = await self._llm_translate(text, "zh", "en", context)
            self._zh_to_en_cache[text] = translated
            return TranslationResult(
                original=text,
                translated=translated,
                language="zh",
                method="llm",
                confidence=0.8
            )
        except Exception as e:
            logger.error(f"LLM翻译失败: {e}")
            return TranslationResult(
                original=text,
                translated=text,
                language="zh",
                method="fallback",
                confidence=0.0
            )
    
    async def _llm_translate(
        self, 
        text: str, 
        from_lang: str, 
        to_lang: str,
        context: str
    ) -> str:
        """使用LLM进行翻译"""
        lang_map = {
            "zh": "中文",
            "en": "English"
        }
        
        system_prompt = f"""你是一个专业的足球术语翻译专家。
请将以下{lang_map[from_lang]}翻译为{lang_map[to_lang]}。

要求：
1. 保持足球术语的专业性
2. 只返回翻译结果，不要解释
3. 如果是球队名称，保留英文原名并加上常用中文称呼
"""
        
        user_prompt = f"上下文: {context}\n\n翻译: {text}"
        
        response = await llm_client.generate(system_prompt, user_prompt)
        return response.strip()
    
    async def translate_data_to_chinese(
        self, 
        data: Dict, 
        fields_to_translate: List[str]
    ) -> Dict:
        """
        翻译数据字典中的指定字段
        
        Args:
            data: 数据字典
            fields_to_translate: 需要翻译的字段列表
            
        Returns:
            翻译后的数据字典
        """
        result = data.copy()
        
        for field in fields_to_translate:
            if field in result and isinstance(result[field], str):
                translation = await self.translate_to_chinese(
                    result[field],
                    context=f"football_{field}"
                )
                result[f"{field}_zh"] = translation.translated
        
        return result
    
    def format_bilingual_text(
        self, 
        english_text: str, 
        chinese_text: str,
        prefer_chinese: bool = True
    ) -> str:
        """
        格式化双语文本
        
        Args:
            english_text: 英文文本
            chinese_text: 中文文本
            prefer_chinese: 是否优先显示中文
            
        Returns:
            格式化的文本，如"Manchester United (曼联)"
        """
        if prefer_chinese and chinese_text:
            if english_text:
                return f"{chinese_text} ({english_text})"
            return chinese_text
        else:
            if chinese_text:
                return f"{english_text} ({chinese_text})"
            return english_text


# 全局单例
translation_helper = TranslationHelper()


# 便捷函数
async def translate_to_chinese(text: str) -> str:
    """便捷函数：翻译为中文"""
    result = await translation_helper.translate_to_chinese(text)
    return result.translated


async def translate_to_english(text: str) -> str:
    """便捷函数：翻译为英文"""
    result = await translation_helper.translate_to_english(text)
    return result.translated


# 测试代码
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 80)
        print("翻译助手测试")
        print("=" * 80)
        
        # 测试语言检测
        test_cases = [
            "Manchester United",
            "曼联",
            "recent matches",
            "最近比赛",
            "Liverpool 利物浦",
        ]
        
        for text in test_cases:
            lang = translation_helper.detect_language(text)
            print(f"\n文本: {text}")
            print(f"语言: {lang}")
        
        # 测试翻译
        print("\n" + "=" * 80)
        print("英译中测试")
        print("=" * 80)
        
        en_texts = ["match", "standings", "recent form"]
        for text in en_texts:
            result = await translation_helper.translate_to_chinese(text)
            print(f"\n原文: {result.original}")
            print(f"译文: {result.translated}")
            print(f"方法: {result.method}")
        
        # 测试双语格式化
        print("\n" + "=" * 80)
        print("双语格式化测试")
        print("=" * 80)
        
        formatted = translation_helper.format_bilingual_text(
            "Manchester United",
            "曼联",
            prefer_chinese=True
        )
        print(f"格式化结果: {formatted}")
    
    asyncio.run(test())

