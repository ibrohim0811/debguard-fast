import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
# ✅ Async Engine funksiyasini import qilamiz
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Modellaringiz va bazangiz importlari
from database import Base, DATABASE_URL
from models import Users, TransactionHistory, ScanHistory, WebApplications

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# database.py faylingizdagi asyncpg URL-ni o'rnatamiz
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Offline rejimda migratsiya."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Sinxron kontekstda migratsiyani bajaruvchi yordamchi funksiya."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """AsyncEngine orqali ulanib, migratsiyani asinxron ishga tushirish."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online rejimda event loop orqali asinxron funksiyani chaqirish."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()