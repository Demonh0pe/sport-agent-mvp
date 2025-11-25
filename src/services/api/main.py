from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.services.api.routers import agent
from src.shared.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Sport Agent API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agent.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}

if __name__ == "__main__":
    import uvicorn
    # 从配置中读取 host 和 port，不再写死！
    uvicorn.run(app, host=settings.service.api.host, port=settings.service.api.port)