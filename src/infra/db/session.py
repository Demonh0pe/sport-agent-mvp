"""
数据库会话管理

功能：
1. 创建异步数据库引擎（带连接池优化）
2. 提供会话工厂
3. 依赖注入函数（FastAPI）
4. 上下文管理器（Service层）
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.shared.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 构造连接串: postgresql+asyncpg://user:pass@host:port/db
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.db.default.user}:{settings.db.default.password}"
    f"@{settings.db.default.host}:{settings.db.default.port}/{settings.db.default.database}"
)

# ============ 连接池配置 ============
# 
# pool_size: 连接池中保持的连接数
# max_overflow: 超出 pool_size 后允许的额外连接数
# pool_timeout: 等待获取连接的超时时间（秒）
# pool_recycle: 连接回收时间（秒），防止数据库断开长时间空闲连接
# pool_pre_ping: 每次使用连接前检查连接是否有效
#
# 企业级配置建议：
# - 小规模（<100 QPS）: pool_size=10, max_overflow=5
# - 中规模（100-500 QPS）: pool_size=20, max_overflow=10
# - 大规模（>500 QPS）: pool_size=50, max_overflow=20, 考虑连接池代理如 PgBouncer
#

# 从配置读取或使用默认值
POOL_SIZE = getattr(settings.db.default, 'pool_size', 20)
MAX_OVERFLOW = getattr(settings.db.default, 'max_overflow', 10)
POOL_TIMEOUT = getattr(settings.db.default, 'pool_timeout', 30)
POOL_RECYCLE = getattr(settings.db.default, 'pool_recycle', 1800)  # 30分钟

# 创建异步引擎（带连接池优化）
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 生产环境关闭 SQL 日志
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # 连接健康检查
)

logger.info(
    f"Database engine created: pool_size={POOL_SIZE}, "
    f"max_overflow={MAX_OVERFLOW}, pool_timeout={POOL_TIMEOUT}s, "
    f"pool_recycle={POOL_RECYCLE}s"
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


# ============ 依赖注入 ============

async def get_db():
    """
    依赖注入函数（供 FastAPI 路由使用）
    
    使用方式:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(query)
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============ 上下文管理器 ============

def get_async_session():
    """
    获取异步数据库会话（上下文管理器）
    
    供 Service 层使用：
        async with get_async_session() as session:
            result = await session.execute(query)
            ...
    
    注意：此函数返回的是 AsyncSession 实例，可直接用作上下文管理器
    """
    return AsyncSessionLocal()


# ============ 连接池监控（可选） ============

async def get_pool_status() -> dict:
    """
    获取连接池状态（用于监控和诊断）
    
    Returns:
        包含连接池状态的字典
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidated(),
    }


async def dispose_engine():
    """
    关闭数据库引擎（应用关闭时调用）
    """
    await engine.dispose()
    logger.info("Database engine disposed")
