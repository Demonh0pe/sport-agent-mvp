from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.shared.config import get_settings

settings = get_settings()

# 构造连接串: postgresql+asyncpg://user:pass@host:port/db
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.db.default.user}:{settings.db.default.password}"
    f"@{settings.db.default.host}:{settings.db.default.port}/{settings.db.default.database}"
)

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 依赖注入函数 (供 FastAPI 使用)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 上下文管理器 (供 Service 层使用)
def get_async_session():
    """
    获取异步数据库会话（上下文管理器）
    
    使用方式:
        async with get_async_session() as session:
            result = await session.execute(query)
    """
    return AsyncSessionLocal()