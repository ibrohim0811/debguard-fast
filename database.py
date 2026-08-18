import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()
# 1. URL'ga +asyncpg qo'shing
DATABASE_URL = "postgresql+asyncpg://postgres:ibrohim0811@postgres:5432/devguard"

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
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()