"""
SupervisorAgent - 监督智能体

职责：
1. 任务规划 (TaskPlanner) - 将用户查询拆解为子任务
2. 专家调度 (ExpertOrchestrator) - 选择并调用合适的专家智能体
3. 结果验证 (ResultValidator) - 质检专家返回的结果
4. 答案合成 (AnswerSynthesizer) - 生成最终自然语言回答

基于 LangChain 实现，使用 Expert-as-Tool 模式
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory  # TODO: Deprecated - 迁移到新的 Memory API

from src.shared.llm_client_v2 import get_llm_client

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    监督智能体
    
    设计理念：
    - 接收用户查询
    - 识别意图并规划子任务
    - 调用 Expert Tools 获取专业信息
    - 验证结果并合成最终回答
    
    实现方式：
    - 基于 LangChain AgentExecutor
    - Expert Agents 通过 Tools 暴露
    - 支持会话上下文记忆
    """
    
    def __init__(
        self,
        expert_tools: List[Any],
        llm_client_instance = None,
        enable_memory: bool = True
    ):
        """
        初始化监督智能体
        
        Args:
            expert_tools: 专家工具列表（从 ExpertRegistry 获取）
            llm_client_instance: LLM 客户端实例
            enable_memory: 是否启用会话记忆
        """
        self._expert_tools = expert_tools
        self._llm_client = llm_client_instance or get_llm_client()
        self._enable_memory = enable_memory
        
        # 获取 LangChain ChatModel
        self._llm = self._llm_client.as_langchain_chat_model()
        
        # 创建 Prompt
        self._prompt = self._create_supervisor_prompt()
        
        # 创建 Agent Executor
        self._agent_executor = self._create_agent_executor()
        
        logger.info(f"SupervisorAgent initialized with {len(expert_tools)} expert tools")
    
    def _create_supervisor_prompt(self) -> ChatPromptTemplate:
        """
        创建 Supervisor 的 System Prompt（Structured Chat 格式）
        
        指导 LLM：
        - 如何理解用户意图
        - 如何选择和调用专家工具
        - 如何组织和呈现答案
        """
        system_message = """你是 Sport Agent 的监督智能体，负责调度多个专家智能体来回答用户的足球相关问题。

## 可用专家工具

{tools}

## 工作流程

1. **理解意图**：分析用户问题，结合对话历史判断需要哪类信息
2. **调用专家**：选择合适的专家工具获取信息
3. **验证结果**：检查返回结果是否完整
4. **合成答案**：整合专家结果，生成自然语言回答

## 上下文理解（重要！）

当用户问题包含指代词（如"那XX呢"、"他们"、"这个队"）时：
- 回顾之前的对话，理解用户在问什么
- 例如：用户先问"曼联最近状态"，再问"那利物浦呢"，应理解为问"利物浦最近状态"
- 自动补全用户的问题意图，调用相应的工具

## 核心原则

- [OK] 所有数据必须来自工具返回
- [OK] 工具返回什么就说什么
- [OK] 数据缺失时诚实告知
- [OK] 理解上下文，自动补全追问意图
- [禁止] 绝不编造数据
- [禁止] 绝不猜测答案
- [禁止] 遇到追问时不要反问用户，直接根据上下文理解并调用工具

## 响应格式

调用工具时使用：

```json
{{{{
    "action": "工具名称",
    "action_input": "查询内容字符串"
}}}}
```

给出最终答案时使用：

```json
{{{{
    "action": "Final Answer",
    "action_input": "你的最终答案"
}}}}
```

可用工具名称: {tool_names}
"""

        human_template = """对话历史：
{chat_history}

当前问题：{input}

{agent_scratchpad}"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_template),
        ])
        
        return prompt
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        创建 LangChain AgentExecutor（使用 Structured Chat 模式，正确解析 JSON 参数）
        
        Returns:
            配置好的 AgentExecutor
        """
        # 创建 Structured Chat Agent（正确处理 JSON 格式参数）
        agent = create_structured_chat_agent(
            llm=self._llm,
            tools=self._expert_tools,
            prompt=self._prompt
        )
        
        # 创建 Memory（如果启用）
        # TODO: ConversationBufferMemory 已被 LangChain 标记为 deprecated
        # 未来升级时需迁移到新的 RunnableConfig/ChatMessageHistory API
        # 参考：https://python.langchain.com/docs/modules/memory/
        memory = None
        if self._enable_memory:
            from langchain.memory import ConversationBufferMemory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="output"
            )
        
        # 创建 Executor
        executor = AgentExecutor(
            agent=agent,
            tools=self._expert_tools,
            memory=memory,  # 添加记忆
            verbose=True,
            max_iterations=10,  # 增加到10次迭代,确保复杂任务能完成
            early_stopping_method="force",  # 修复: 使用 "force" 替代已废弃的 "generate"
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        return executor
    
    async def run(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户查询的主入口
        
        Args:
            query: 用户自然语言查询
            session_id: 会话 ID（用于记忆管理）
            context: 额外上下文信息
            
        Returns:
            {
                "answer": str,              # 最终自然语言回答
                "intermediate_steps": [],   # 中间步骤（调试用）
                "tools_used": [],           # 使用的工具列表
                "session_id": str,
                "timestamp": str
            }
        """
        logger.info(f"[Supervisor] Processing query: {query}")
        start_time = datetime.now()
        
        try:
            # 准备输入
            inputs = {
                "input": query
            }
            
            # 如果有上下文，追加到输入
            if context:
                inputs.update(context)
            
            # 调用 Agent Executor
            result = await self._agent_executor.ainvoke(inputs)
            
            # 提取结果
            answer = result.get("output", "抱歉，我无法回答这个问题。")
            intermediate_steps = result.get("intermediate_steps", [])
            
            # 提取使用的工具
            tools_used = [
                step[0].tool for step in intermediate_steps
            ]
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[Supervisor] Query completed in {duration:.2f}s, used {len(tools_used)} tools")
            
            return {
                "answer": answer,
                "intermediate_steps": intermediate_steps,
                "tools_used": tools_used,
                "session_id": session_id or "default",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration
            }
            
        except Exception as e:
            logger.error(f"[Supervisor] Error processing query: {e}", exc_info=True)
            return {
                "answer": f"处理您的问题时遇到错误：{str(e)}。请稍后重试或换个方式提问。",
                "intermediate_steps": [],
                "tools_used": [],
                "session_id": session_id or "default",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    # ==================== 结果验证（可选增强） ====================
    
    async def _validate_result(
        self,
        query: str,
        tool_results: List[Any]
    ) -> bool:
        """
        验证工具返回的结果是否足够回答用户问题
        
        Args:
            query: 用户原始问题
            tool_results: 工具返回的结果列表
            
        Returns:
            是否通过验证
        """
        # TODO: 实现 LLM 级别的结果验证
        # 可以调用 LLM 判断：
        # - 结果是否相关
        # - 是否回答了核心问题
        # - 是否需要补充信息
        
        return True  # 暂时总是通过
    
    def get_conversation_history(
        self,
        session_id: str
    ) -> List[Dict[str, str]]:
        """
        获取会话历史（如果启用了 Memory）
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话历史消息列表
        """
        # TODO: 实现基于 session_id 的会话历史管理
        # 可以使用 Redis 或内存存储
        return []

