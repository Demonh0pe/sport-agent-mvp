"""
FastAPI 应用入口

功能：
1. 路由注册
2. 中间件配置（CORS、Trace ID、请求耗时）
3. 健康检查
"""
import time
import uuid
import logging
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.services.api.routers import agent
from src.shared.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 上下文变量：存储 request_id，可在整个请求链路中访问
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """获取当前请求的 Trace ID"""
    return request_id_ctx.get()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Sport Agent API",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============ 中间件 ============

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next) -> Response:
    """
    Trace ID 中间件
    
    功能：
    1. 为每个请求生成唯一的 request_id
    2. 将 request_id 存入上下文变量，供日志使用
    3. 在响应头中返回 X-Request-ID
    4. 记录请求耗时
    """
    # 生成或使用客户端提供的 request_id
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # 存入上下文变量
    token = request_id_ctx.set(request_id)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 记录请求开始
        logger.info(
            f"[{request_id}] Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
            }
        )
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        
        # 记录请求完成
        logger.info(
            f"[{request_id}] Request completed: {response.status_code} in {duration_ms}ms",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        
        return response
    
    except Exception as e:
        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 记录异常
        logger.error(
            f"[{request_id}] Request failed: {str(e)} in {duration_ms}ms",
            extra={
                "request_id": request_id,
                "error": str(e),
                "duration_ms": duration_ms,
            },
            exc_info=True
        )
        raise
    
    finally:
        # 重置上下文变量
        request_id_ctx.reset(token)


# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 路由 ============

app.include_router(agent.router)


# ============ 健康检查 ============

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "version": settings.app_version,
        "service": "sport-agent-api"
    }


@app.get("/ready")
async def readiness_check():
    """就绪检查端点（可扩展检查数据库连接等）"""
    # TODO: 添加数据库连接检查
    # TODO: 添加 LLM 服务检查
    return {
        "status": "ready",
        "version": settings.app_version,
        "checks": {
            "api": "ok",
            # "database": "ok",  # 后续添加
            # "llm": "ok",       # 后续添加
        }
    }


# ============ 启动事件 ============

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info(f"Shutting down {settings.app_name}")


# ============ 直接运行 ============

if __name__ == "__main__":
    import uvicorn
    # 从配置中读取 host 和 port
    uvicorn.run(
        app, 
        host=settings.service.api.host, 
        port=settings.service.api.port
    )
