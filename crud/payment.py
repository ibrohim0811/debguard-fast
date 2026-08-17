from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Users, TransactionHistory, ScanHistory, WebApplications


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