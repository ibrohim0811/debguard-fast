from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Users, TransactionHistory, ScanHistory, WebApplications


async def create_scan_history(webapp_id, result_summary, scan_type, db: AsyncSession):
    sh = ScanHistory(
        webapp_id=webapp_id,
        result_summary=result_summary,
        scan_type=scan_type
    )

    db.add(sh)
    await db.commit()
    await db.refresh(sh)
    return sh


async def get_all_scans(webapp_id, db: AsyncSession):
    stmt = (
        select(WebApplications)
        .where(
            ScanHistory.webapp_id == webapp_id
        )
    )   
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_scan_history(webapp_id, db: AsyncSession):
    stmt = (
        select(WebApplications)
        .where(
            ScanHistory.webapp_id == webapp_id
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()