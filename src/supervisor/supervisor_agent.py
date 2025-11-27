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

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
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
    
    def _create_supervisor_prompt(self) -> PromptTemplate:
        """
        创建 Supervisor 的 System Prompt
        
        指导 LLM：
        - 如何理解用户意图
        - 如何选择和调用专家工具
        - 如何组织和呈现答案
        """
        system_message = """你是 Sport Agent 的监督智能体，负责调度多个专家智能体来回答用户的足球相关问题。

你可以使用以下专家工具：

1. **data_stats_expert**: 用于查询联赛、比赛、球队状态、近期表现、主客场差异等数据和统计信息。
   - 适用场景：查询比赛时间、球队战绩、积分榜、近期状态、主客场表现
   
2. **prediction_expert**: 用于对一场具体比赛输出胜平负概率及相关特征说明。
   - 适用场景：预测比赛结果、分析双方实力对比、给出胜负判断
   
3. **knowledge_expert**: 用于解释足球规则、战术、专业名词和比赛分析逻辑。
   - 适用场景：规则解释、战术分析、足球知识科普

**工作流程要求**：

1. **理解意图**：仔细分析用户问题，判断需要哪些类型的信息。

2. **规划调用**：
   - 如果需要数据支持，先调用 data_stats_expert
   - 如果需要预测，调用 prediction_expert（通常需要先获取数据）
   - 如果需要解释概念，调用 knowledge_expert
   - 可以组合调用多个专家

3. **结果验证**：
   - 检查专家返回的结果是否完整
   - 如果缺少关键信息，考虑追加调用
   - 如果专家无法回答，诚实告知用户

4. **答案合成**：
   - 用自然、流畅的语言整合专家结果
   - 突出关键信息和数据依据
   - 保持客观，不要夸大或编造信息
   - 如果是预测类问题，说明概率和依据

5. **边界意识**：
   - 不要自己臆造数据，所有事实必须来自工具返回
   - 如果工具返回错误或无结果，承认限制
   - 超出系统能力的问题，礼貌拒绝

**核心原则（绝对禁止违反）**：

1. **严格禁止编造数据**：
   - 不允许虚构任何比赛结果、日期、比分
   - 不允许基于"常识"或"假设"给出数据
   - 所有数据必须来自工具返回的真实结果

2. **必须调用工具获取数据**：
   - 对任何需要数据的问题，必须先调用相应工具
   - 不要试图从用户问题中"猜测"答案
   - 工具返回什么就说什么，不要添油加醋

3. **诚实面对数据缺失**：
   - 如果工具返回空结果，直接告知："数据库中没有该数据"
   - 如果调用失败，明确说明："查询失败"
   - 不要用模糊语言掩盖问题

4. **简洁直接的回答**：
   - 直接给出工具返回的数据
   - 不要过度解释或编造背景
   - 保持客观，不要主观臆断

**错误示例（禁止）**：
用户："比萨最近战绩"
错误回答："比萨队在最近的意甲比赛中表现不佳，他们输给了尤文图斯0-2..."
（这是编造的！）

**正确示例**：
用户："比萨最近战绩"
→ 调用 data_stats_expert("比萨")
→ 工具返回：无数据
→ 正确回答："抱歉，数据库中没有比萨队的比赛数据。"

记住：真实性 > 一切

使用以下格式回答：

Question: 用户的问题
Thought: 我需要做什么
Action: 工具名称
Action Input: 工具输入
Observation: 工具返回结果
... (重复直到有答案)
Thought: 我现在知道最终答案了
Final Answer: 基于真实数据的最终答案

可用工具：
{tools}

工具名称：
{tool_names}

开始！

Question: {input}
Thought: {agent_scratchpad}"""
        
        prompt = PromptTemplate.from_template(system_message)
        
        return prompt
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        创建 LangChain AgentExecutor
        
        Returns:
            配置好的 AgentExecutor
        """
        # 创建 ReAct Agent
        agent = create_react_agent(
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

