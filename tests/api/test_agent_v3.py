"""
测试 Agent V3 API

测试内容：
1. POST /api/v1/agent/chat - 对话接口
2. GET /api/v1/agent/experts - 专家列表
"""
import pytest
from httpx import AsyncClient


class TestAgentV3API:
    """Agent V3 API 测试套件"""
    
    @pytest.mark.asyncio
    async def test_chat_basic(self, client: AsyncClient):
        """测试基本对话"""
        response = await client.post(
            "/api/v1/agent/chat",
            json={"query": "曼联最近的比赛情况如何？"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert "answer" in data
        assert "tools_used" in data
        assert "session_id" in data
        assert "timestamp" in data
        assert "duration_seconds" in data
        assert "status" in data
        
        # 验证数据类型
        assert isinstance(data["answer"], str)
        assert isinstance(data["tools_used"], list)
        assert isinstance(data["duration_seconds"], (int, float))
        assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_chat_with_session(self, client: AsyncClient):
        """测试带会话ID的对话"""
        session_id = "test-session-123"
        
        # 第一轮对话
        response1 = await client.post(
            f"/api/v1/agent/chat?session_id={session_id}",
            json={"query": "曼联最近怎么样？"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["session_id"] == session_id
        
        # 第二轮对话（带上下文）
        response2 = await client.post(
            f"/api/v1/agent/chat?session_id={session_id}",
            json={"query": "那利物浦呢？"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_chat_empty_query(self, client: AsyncClient):
        """测试空查询"""
        response = await client.post(
            "/api/v1/agent/chat",
            json={"query": ""}
        )
        
        # 应该返回错误或处理空查询
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_chat_long_query(self, client: AsyncClient):
        """测试长查询"""
        long_query = "请分析" + "曼联" * 100 + "的比赛情况"
        
        response = await client.post(
            "/api/v1/agent/chat",
            json={"query": long_query}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_list_experts(self, client: AsyncClient):
        """测试获取专家列表"""
        response = await client.get("/api/v1/agent/experts")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert "experts" in data
        assert "total" in data
        
        # 验证专家列表
        assert isinstance(data["experts"], list)
        assert len(data["experts"]) > 0
        assert isinstance(data["total"], int)
        
        # 验证包含预期的专家
        experts = data["experts"]
        assert "data_stats" in experts or "prediction" in experts
    
    @pytest.mark.asyncio
    async def test_chat_various_queries(self, client: AsyncClient):
        """测试不同类型的查询"""
        queries = [
            "英超积分榜",
            "曼联 vs 利物浦预测",
            "拜仁最近5场比赛",
            "皇马的主场战绩",
            "什么是越位规则？",
        ]
        
        for query in queries:
            response = await client.post(
                "/api/v1/agent/chat",
                json={"query": query}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["answer"]) > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """测试就绪检查端点"""
        response = await client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestAgentV3Integration:
    """Agent V3 集成测试（需要真实服务）"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_chat_flow(self, client: AsyncClient):
        """
        测试真实对话流程
        
        注意：这个测试需要：
        1. LLM 服务运行（Ollama/OpenAI）
        2. 数据库连接正常
        """
        response = await client.post(
            "/api/v1/agent/chat",
            json={"query": "曼联最近的比赛情况"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证使用了真实工具
        assert len(data["tools_used"]) > 0
        
        # 验证回答包含实际内容
        assert len(data["answer"]) > 50
        
        # 验证耗时合理
        assert data["duration_seconds"] < 30  # 不应超过30秒


class TestAgentV3Performance:
    """Agent V3 性能测试"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_response_time(self, client: AsyncClient):
        """测试响应时间"""
        import time
        
        start = time.time()
        response = await client.post(
            "/api/v1/agent/chat",
            json={"query": "曼联积分榜"}
        )
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 10  # 应在10秒内响应
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client: AsyncClient):
        """测试并发请求"""
        import asyncio
        
        async def make_request(query: str):
            return await client.post(
                "/api/v1/agent/chat",
                json={"query": query}
            )
        
        # 并发5个请求
        queries = [f"查询{i}" for i in range(5)]
        tasks = [make_request(q) for q in queries]
        
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200

