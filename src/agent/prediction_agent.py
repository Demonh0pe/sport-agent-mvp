"""
PredictionAgent - 预测专家智能体

职责：
1. 处理比赛预测相关的查询
2. 调用 PredictService 获取预测结果
3. 提供可解释的预测分析

实现方式：
- 基于 LangChain AgentExecutor
- 使用 PredictTool
- 依赖 PredictService（纯 Python 业务逻辑）
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from src.services.predict_service import predict_service

if TYPE_CHECKING:
    from src.shared.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ==================== Tool Schemas ====================

class PredictMatchInput(BaseModel):
    """预测比赛的输入"""
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")


# ==================== PredictionAgent ====================

class PredictionAgent:
    """
    预测专家智能体
    
    擅长回答：
    - "阿森纳对曼城谁会赢？"
    - "明天曼联对利物浦的比赛，预测结果如何？"
    - "为什么你认为主队会赢？"
    """
    
    def __init__(self, llm_client: 'LLMClient'):
        """
        初始化预测专家
        
        Args:
            llm_client: LLM 客户端实例
        """
        self._llm_client = llm_client
        self._llm = llm_client.as_langchain_chat_model()
        
        # 创建工具
        self._tools = self._create_tools()
        
        # 创建 Prompt
        self._prompt = self._create_prompt()
        
        # 创建 Agent Executor
        self._agent_executor = self._create_agent_executor()
        
        logger.info(f"PredictionAgent initialized with {len(self._tools)} tools")
    
    def _create_tools(self):
        """创建预测工具"""
        
        async def predict_match_impl(home_team: str, away_team: str) -> str:
            """
            预测比赛结果
            
            Args:
                home_team: 主队名称
                away_team: 客队名称
                
            Returns:
                预测结果的自然语言描述
            """
            try:
                # 调用 PredictService
                prediction = await predict_service.predict_match(
                    home_team_name=home_team,
                    away_team_name=away_team
                )
                
                if not prediction:
                    return f"无法预测 {home_team} vs {away_team}，数据不足"
                
                # 格式化输出
                result_cn = {
                    "HOME_WIN": f"{home_team}获胜",
                    "DRAW": "平局",
                    "AWAY_WIN": f"{away_team}获胜"
                }
                
                output_lines = [
                    f"【{home_team} vs {away_team} 预测分析】\n",
                    f"预测结果: {result_cn[prediction.predicted_outcome]}",
                    f"置信度: {prediction.confidence:.1%}\n",
                    
                    f"概率分布:",
                    f"- {home_team}获胜: {prediction.home_win_prob:.1%}",
                    f"- 平局: {prediction.draw_prob:.1%}",
                    f"- {away_team}获胜: {prediction.away_win_prob:.1%}\n",
                    
                    f"关键影响因素:"
                ]
                
                for i, factor in enumerate(prediction.key_factors, 1):
                    output_lines.append(f"{i}. {factor}")
                
                output_lines.extend([
                    f"\n模型版本: {prediction.model_version}",
                    f"数据质量评分: {prediction.data_quality_score:.2f}/1.0"
                ])
                
                return "\n".join(output_lines)
                
            except Exception as e:
                logger.error(f"predict_match failed: {e}")
                return f"预测失败：{str(e)}"
        
        # 使用 StructuredTool 包装，并指定 args_schema
        tools = [
            StructuredTool.from_function(
                coroutine=predict_match_impl,
                name="predict_match",
                description=(
                    "预测两队比赛的胜平负结果。\n"
                    "输入：主队名称（home_team）和客队名称（away_team）\n"
                    "输出：预测结果、概率分布、置信度和关键影响因素"
                ),
                args_schema=PredictMatchInput
            )
        ]
        
        return tools
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """创建 Agent Prompt（Structured Chat 格式）"""
        
        system_message = """你是预测专家，擅长分析足球比赛的胜负走势。

## 可用工具

{tools}

## 工作要求

1. 从用户问题中提取主队和客队名称
2. 调用预测工具获取结果
3. 用专业但易懂的语言解释预测
4. 强调这是基于数据的概率预测，不是绝对结果
5. 指出关键影响因素和不确定性

## 回答风格

- 客观理性，不夸大
- 数据驱动，有理有据
- 突出概率和关键因素
- 提示预测的局限性

## 注意事项

- 如果用户问题中没有明确的主客队，询问澄清
- 如果数据质量低，明确告知用户
- 避免绝对化的表述（如"一定会赢"）

## 响应格式

请使用以下 JSON 格式调用工具：

```json
{{{{
    "action": "predict_match",
    "action_input": {{{{
        "home_team": "主队名称",
        "away_team": "客队名称"
    }}}}
}}}}
```

当你有了最终答案时，使用：

```json
{{{{
    "action": "Final Answer",
    "action_input": "你的最终答案"
}}}}
```

可用工具名称: {tool_names}
"""

        human_template = """{input}

{agent_scratchpad}"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template),
        ])
        
        return prompt
    
    def _create_agent_executor(self) -> AgentExecutor:
        """创建 Agent Executor（使用 Structured Chat 模式，正确解析 JSON 参数）"""
        agent = create_structured_chat_agent(
            llm=self._llm,
            tools=self._tools,
            prompt=self._prompt
        )
        
        executor = AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=True,
            max_iterations=8,  # 预测通常需要更多步骤
            early_stopping_method="force",  # 使用 "force" 而不是已废弃的 "generate"
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        return executor
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        同步执行查询
        
        Args:
            query: 用户查询
            
        Returns:
            结果字典
        """
        try:
            result = self._agent_executor.invoke({"input": query})
            return {
                "output": result.get("output", ""),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"PredictionAgent.run failed: {e}")
            return {
                "output": f"预测时出错：{str(e)}",
                "status": "error"
            }
    
    async def arun(self, query: str) -> Dict[str, Any]:
        """
        异步执行查询
        
        Args:
            query: 用户查询
            
        Returns:
            结果字典
        """
        try:
            result = await self._agent_executor.ainvoke({"input": query})
            return {
                "output": result.get("output", ""),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"PredictionAgent.arun failed: {e}")
            return {
                "output": f"预测时出错：{str(e)}",
                "status": "error"
            }

