from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from .models import Base

# Исправляем URL для asyncpg
def get_async_database_url():
    if DATABASE_URL.startswith("postgresql+asyncpg://"):
        # Убираем +asyncpg для asyncpg драйвера
        return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return DATABASE_URL

# Создаем асинхронный движок с правильным URL
engine = create_async_engine(get_async_database_url(), echo=True)

# Остальное без изменений...
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def create_tables():
    """Создает все таблицы в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()