from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Users, TransactionHistory, ScanHistory, WebApplications, TransactionStatus


async def get_last_scan(webapp_id: int, db: AsyncSession):
    # ✅ select, desc() va scalars().first() ishlatilishi kerak
    stmt = (
        select(ScanHistory)
        .where(ScanHistory.webapp_id == webapp_id)
        .order_by(ScanHistory.scanned_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def transaction_create(webapp_id: int, user_id: int, status: str, amount: float, db: AsyncSession):
    tx = TransactionHistory(
        webapp_id=webapp_id,
        user_id=user_id,
        status=status,
        amount=amount   
    )
    # ✅ db.add() oldidan await OLIB TASHLANDI
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def get_webapp_by_slug_and_user(slug: str, user_id: int, db: AsyncSession) -> Optional[WebApplications]:
    stmt = (
        select(WebApplications)
        .where(
            WebApplications.slug == slug,
            WebApplications.user_id == user_id
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_my_transactions(user_id: int, db: AsyncSession):
    transactions = (
        select(TransactionHistory).where(TransactionHistory.user_id==user_id)
    )
    result = await db.execute(transactions)
    return result.scalars().all()


async def get_my_transaction(user_id: int, payment_id: str, db: AsyncSession):
    transactions = (
        select(TransactionHistory).where(TransactionHistory.user_id==user_id, TransactionHistory.payment_id == payment_id)
    )
    result = await db.execute(transactions)
    return result.scalar_one_or_none()


async def get_transaction_webapp(user_id, webapp_id, db: AsyncSession):
    transaction = (
        select(TransactionHistory).where(TransactionHistory.user_id==user_id, TransactionHistory.webapp_id==webapp_id)
    )
    response = await db.execute(transaction)
    return response.scalars().all()



async def get_last_successful_transaction(webapp_id: int, user_id: int, db: AsyncSession) -> TransactionHistory | None:
    query = (
        select(TransactionHistory)
        .where(
            TransactionHistory.webapp_id == webapp_id,
            TransactionHistory.user_id == user_id,
            TransactionHistory.status == TransactionStatus.SUCCESS  # yoki sizda TransactionStatus.SUCCESS bo'lsa shuni yozasiz
        )
        .order_by(TransactionHistory.payment_date.desc())
    )
    result = await db.execute(query)
    return result.scalars().first()


# 2. Hali to'lanmagan (PENDING) tranzaksiya bor-yo'qligini tekshirish
# (Har safar yangi PENDING tranzaksiya yaratavermaslik uchun)
async def get_pending_transaction(webapp_id: int, user_id: int, db: AsyncSession) -> TransactionHistory | None:
    query = (
        select(TransactionHistory)
        .where(
            TransactionHistory.webapp_id == webapp_id,
            TransactionHistory.user_id == user_id,
            TransactionHistory.status == TransactionStatus.PENDING
        )
        .order_by(TransactionHistory.payment_date.desc())
    )
    result = await db.execute(query)
    return result.scalars().first()