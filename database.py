from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager

# 1. URL'ga +asyncpg qo'shing
DATABASE_URL = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/devguard"

# 2. create_async_engine ishlatishingiz shart
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. AsyncSessionLocal tayyorlash
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# 4. Asinxron get_db generatori
@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session