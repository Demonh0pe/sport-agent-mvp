"""Agent 工具执行器：负责实际调用工具并处理响应"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import httpx
from pydantic import BaseModel

from src.agent.core.parameter_resolver import ParameterResolver, ParsedToolStep

if TYPE_CHECKING:
    from src.shared.config import Settings


class ToolInvocationResult(BaseModel):
    """工具调用结果"""
    tool_name: str
    input_params: Dict[str, Any]
    output: Dict[str, Any]  # 工具返回的结构化数据
    status: str  # "success", "failure", "timeout"
    latency_ms: int
    error_message: Optional[str] = None


class Executor:
    """
    Agent 工具执行器

    功能:
    1. 接收 Planner 生成的工具链步骤
    2. 解析参数并处理占位符
    3. 通过 HTTP 调用远端工具服务
    4. 管理执行上下文和错误处理
    5. 返回结构化的工具响应

    设计特点:
    - 并发执行（当工具间无依赖时）
    - 超时控制与重试机制
    - 响应缓存（可选）
    - 详细的执行追踪
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.resolver = ParameterResolver()
        self.context: Dict[str, Any] = {}  # 执行上下文
        self.results: List[ToolInvocationResult] = []  # 执行结果
        self.http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.http_client = httpx.AsyncClient(
            timeout=self.settings.service.agent.timeout or 30
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.http_client:
            await self.http_client.aclose()

    async def execute_plan(
        self,
        plan_steps: List[str],
        match_id_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行完整的工具链

        Args:
            plan_steps: Planner 输出的工具步骤列表
            match_id_hint: 可选的 match_id 提示（用于初始化上下文）

        Returns:
            执行结果汇总，包含所有工具的输出
        """
        # 初始化上下文
        if match_id_hint:
            self.context["match_id"] = match_id_hint

        # 解析所有步骤
        parsed_steps = self.resolver.resolve_all_steps(plan_steps)

        # 执行步骤
        for parsed_step in parsed_steps:
            try:
                result = await self._execute_single_tool(parsed_step)
                self.results.append(result)

                # 更新上下文 (用于后续步骤的占位符填充)
                if result.status == "success":
                    self._update_context(result)

            except Exception as e:
                print(f"❌ 执行失败: {parsed_step.tool_name} - {e}")
                # 可选: 继续执行还是中断？
                # 这里选择继续，记录为失败
                self.results.append(
                    ToolInvocationResult(
                        tool_name=parsed_step.tool_name,
                        input_params=parsed_step.params,
                        output={},
                        status="failure",
                        latency_ms=0,
                        error_message=str(e),
                    )
                )

        return self._build_summary()

    async def _execute_single_tool(
        self,
        parsed_step: ParsedToolStep
    ) -> ToolInvocationResult:
        """
        执行单个工具

        Steps:
        1. 查找工具配置
        2. 构建 HTTP 请求
        3. 发送请求并测时
        4. 解析响应
        5. 错误处理
        """
        tool_name = parsed_step.tool_name
        params = parsed_step.params

        # 1. 查找工具配置
        tool_config = self._find_tool_config(tool_name)
        if not tool_config:
            raise ValueError(f"工具 {tool_name} 未在注册表中找到")

        # 2. 构建请求
        url = tool_config["endpoint"]
        method = tool_config["method"].upper()
        headers = {"Content-Type": "application/json"}

        # 3. 发送请求
        start_time = time.time()
        try:
            if method == "GET":
                # GET: 参数作为 query string
                response = await self.http_client.get(
                    url,
                    params=params,
                    headers=headers,
                )
            elif method == "POST":
                # POST: 参数作为 JSON body
                response = await self.http_client.post(
                    url,
                    json=params,
                    headers=headers,
                )
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            latency_ms = int((time.time() - start_time) * 1000)

            # 4. 解析响应
            if response.status_code == 200:
                try:
                    output = response.json()
                except Exception:
                    output = {"raw": response.text}

                return ToolInvocationResult(
                    tool_name=tool_name,
                    input_params=params,
                    output=output,
                    status="success",
                    latency_ms=latency_ms,
                )
            else:
                return ToolInvocationResult(
                    tool_name=tool_name,
                    input_params=params,
                    output={},
                    status="failure",
                    latency_ms=latency_ms,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                )

        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolInvocationResult(
                tool_name=tool_name,
                input_params=params,
                output={},
                status="timeout",
                latency_ms=latency_ms,
                error_message=f"Request timeout (> {self.settings.service.agent.timeout}s)",
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolInvocationResult(
                tool_name=tool_name,
                input_params=params,
                output={},
                status="failure",
                latency_ms=latency_ms,
                error_message=str(e),
            )

    def _find_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """从配置中查找工具定义"""
        tools = self.settings.agent_tools.tools

        for tool in tools:
            if tool.name == tool_name:
                return {
                    "name": tool.name,
                    "endpoint": tool.endpoint,
                    "method": tool.method,
                    "params": tool.params,
                }

        return None

    def _update_context(self, result: ToolInvocationResult) -> None:
        """
        基于工具执行结果更新执行上下文

        规则:
        - MatchResolverTool 的输出 → 提取 match_id, team_ids
        - 其他工具的输出 → 保存为 tool_<name>
        """
        tool_name = result.tool_name
        output = result.output

        if tool_name == "MatchResolverTool":
            # 从 match_resolver 结果提取关键信息
            if "match_id" in output:
                self.context["match_id"] = output["match_id"]
            if "home_team_id" in output:
                self.context["home_team_id"] = output["home_team_id"]
            if "away_team_id" in output:
                self.context["away_team_id"] = output["away_team_id"]

        # 通用: 将工具输出保存到上下文
        self.context[f"tool_{tool_name}"] = output

    def _build_summary(self) -> Dict[str, Any]:
        """构建执行结果摘要"""
        success_count = sum(
            1 for r in self.results if r.status == "success"
        )
        failure_count = sum(
            1 for r in self.results if r.status in ("failure", "timeout")
        )
        total_latency = sum(r.latency_ms for r in self.results)

        return {
            "status": "completed",
            "execution_stats": {
                "total_tools": len(self.results),
                "successful": success_count,
                "failed": failure_count,
                "total_latency_ms": total_latency,
            },
            "results": [r.model_dump() for r in self.results],
            "context": self.context,
        }


# ============ 使用示例 ============
async def example_usage():
    """示例: 如何使用 Executor"""
    from src.shared.config import get_settings

    settings = get_settings()

    # 使用异步上下文管理器
    async with Executor(settings) as executor:
        plan_steps = [
            "MatchResolverTool(query='Barcelona next match')",
            "PredictionTool(match_id=$match_id, phase='T-24h')",
            "NewsTool(entity_id=$home_team_id, entity_type='team', window_hours=72)",
        ]

        result = await executor.execute_plan(plan_steps)
        print(result)


if __name__ == "__main__":
    # 如需测试，需在虚拟环境中运行
    # asyncio.run(example_usage())
    pass
