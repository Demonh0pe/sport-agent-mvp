"""参数解析与绑定系统：将 Planner 的工具链步骤转换为可执行的参数"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ValidationError


class ParsedToolStep(BaseModel):
    """解析后的工具调用步骤"""
    tool_name: str
    raw_params: Dict[str, str]  # 原始参数（可能包含占位符）
    params: Dict[str, Any] = {}  # 解析后的参数


class ParameterResolver:
    """
    功能：
    1. 从 Planner 步骤字符串解析出工具名和参数
    2. 处理占位符 ($match_id, $entity_id) 的绑定
    3. 参数类型转换与验证

    示例:
        input:  "PredictionTool(match_id=$match_id, phase='T-24h')"
        output: ParsedToolStep(
                    tool_name="PredictionTool",
                    raw_params={"match_id": "$match_id", "phase": "T-24h"},
                    params={"match_id": "man-utd-001", "phase": "T-24h"}  # 填充后
                )
    """

    # 正则: 匹配 ToolName(param1=val1, param2=val2, ...)
    TOOL_STEP_PATTERN = re.compile(
        r"([a-zA-Z]+Tool)\s*\((.*)\)$",
        re.IGNORECASE
    )

    # 占位符前缀
    PLACEHOLDER_PREFIX = "$"

    def __init__(self):
        """初始化参数解析器"""
        self.context: Dict[str, Any] = {}  # 执行上下文，存放前一步的输出

    def parse_step(self, step: str) -> ParsedToolStep:
        """
        解析单个工具步骤字符串

        Args:
            step: "ToolName(param1=val1, param2=val2, ...)"

        Returns:
            ParsedToolStep

        Raises:
            ValueError: 格式不符合或解析失败
        """
        step = step.strip()
        match = self.TOOL_STEP_PATTERN.match(step)

        if not match:
            raise ValueError(f"无法解析工具步骤: {step}")

        tool_name = match.group(1)
        params_str = match.group(2)

        # 解析参数字符串
        raw_params = self._parse_params(params_str)

        return ParsedToolStep(
            tool_name=tool_name,
            raw_params=raw_params
        )

    def _parse_params(self, params_str: str) -> Dict[str, str]:
        """
        解析参数字符串，支持:
        - key='string value'
        - key=$placeholder
        - key=123 (数字)
        - key=[1,2,3] (数组)

        例:
            "match_id=$match_id, phase='T-24h', limit=5"
            =>
            {"match_id": "$match_id", "phase": "'T-24h'", "limit": "5"}
        """
        if not params_str.strip():
            return {}

        params = {}
        # 简单的参数提取（处理基本情况）
        # 更复杂的情况可用 ast.literal_eval
        parts = self._split_params(params_str)

        for part in parts:
            if "=" not in part:
                continue

            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()

            params[key] = val

        return params

    def _split_params(self, params_str: str) -> List[str]:
        """
        分割参数字符串，处理嵌套和引号

        示例:
            "a='hello, world', b=123"
            => ["a='hello, world'", "b=123"]
        """
        parts = []
        current = ""
        in_quote = False
        quote_char = None

        for char in params_str:
            if char in ("'", '"') and (not in_quote or quote_char == char):
                in_quote = not in_quote
                quote_char = char if in_quote else None
                current += char
            elif char == "," and not in_quote:
                if current.strip():
                    parts.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            parts.append(current.strip())

        return parts

    def resolve_placeholders(
        self,
        parsed_step: ParsedToolStep,
        context: Dict[str, Any]
    ) -> ParsedToolStep:
        """
        使用执行上下文填充占位符

        Args:
            parsed_step: 已解析的步骤
            context: 执行上下文，通常包含前一步的输出
                    {"match_id": "man-utd-001", "entity_id": "Messi", ...}

        Returns:
            填充后的 ParsedToolStep

        Raises:
            KeyError: 占位符在上下文中找不到
        """
        resolved_params = {}

        for key, val in parsed_step.raw_params.items():
            val_str = str(val)

            # 处理占位符
            if val_str.startswith(self.PLACEHOLDER_PREFIX):
                placeholder_key = val_str[len(self.PLACEHOLDER_PREFIX):]

                if placeholder_key not in context:
                    raise KeyError(
                        f"占位符 ${placeholder_key} 在上下文中未找到。"
                        f"可用的上下文: {list(context.keys())}"
                    )

                resolved_params[key] = context[placeholder_key]
            else:
                # 移除引号
                resolved_params[key] = self._unquote(val_str)

        # 创建新的 ParsedToolStep
        parsed_step.params = resolved_params
        return parsed_step

    def _unquote(self, value: str) -> Any:
        """
        移除字符串两端的引号，并尝试类型转换

        示例:
            "'T-24h'" => "T-24h"
            "123" => 123
            "[1, 2, 3]" => [1, 2, 3]
        """
        value = value.strip()

        # 字符串
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return value[1:-1]

        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 布尔值
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # 数组/列表 (简单处理)
        if value.startswith("[") and value.endswith("]"):
            try:
                import ast
                return ast.literal_eval(value)
            except Exception:
                pass

        # 默认返回原始字符串
        return value

    def resolve_all_steps(
        self,
        steps: List[str]
    ) -> List[ParsedToolStep]:
        """
        解析并绑定多个工具步骤，自动处理依赖关系

        逻辑:
        1. 逐步解析每个步骤
        2. 执行到某个步骤时，用前一步的输出作为上下文
        3. 填充占位符

        Args:
            steps: Planner 输出的步骤列表

        Returns:
            填充后的 ParsedToolStep 列表
        """
        resolved_steps: List[ParsedToolStep] = []
        context: Dict[str, Any] = {}

        for step in steps:
            try:
                # 1. 解析
                parsed = self.parse_step(step)

                # 2. 填充占位符 (如果有的话)
                if any(v.startswith(self.PLACEHOLDER_PREFIX)
                       for v in parsed.raw_params.values()):
                    try:
                        parsed = self.resolve_placeholders(parsed, context)
                    except KeyError as e:
                        # 占位符无法填充，先保留原始形式
                        # Executor 会在真实执行时处理
                        print(f"⚠️ 占位符未能解析: {e}")
                        parsed.params = parsed.raw_params

                resolved_steps.append(parsed)

                # 3. 更新上下文 (为下一步做准备)
                # 这里假设工具输出包含一些关键信息
                # 实际需要等 Executor 执行后才能更新

            except ValueError as e:
                print(f"❌ 解析失败: {step} - {e}")
                raise

        return resolved_steps


# ============ 使用示例 ============
if __name__ == "__main__":
    resolver = ParameterResolver()

    # 示例 1: 简单参数
    step1 = "MatchResolverTool(query='Manchester United next match')"
    parsed1 = resolver.parse_step(step1)
    print(f"✅ 步骤 1 解析: {parsed1}")

    # 示例 2: 含占位符
    step2 = "PredictionTool(match_id=$match_id, phase='T-24h')"
    parsed2 = resolver.parse_step(step2)
    print(f"✅ 步骤 2 解析: {parsed2}")

    # 示例 3: 填充占位符
    context = {"match_id": "man-utd-001"}
    resolved2 = resolver.resolve_placeholders(parsed2, context)
    print(f"✅ 填充后: {resolved2.params}")
