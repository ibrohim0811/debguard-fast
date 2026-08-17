from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import WebApplications


async def create_webapp(
    domain: str, 
    user_id: int, 
    title: str, 
    is_subdomain: Optional[bool], 
    db: AsyncSession
) -> WebApplications:
    webapp = WebApplications(
        domain=domain,
        user_id=user_id,
        title=title,
        is_subdomain=is_subdomain if is_subdomain is not None else False
    )
    db.add(webapp)  # await shart emas
    await db.commit()  # await shart
    await db.refresh(webapp)  # await shart
    return webapp


async def get_webapps(user_id: int, db: AsyncSession) -> List[WebApplications]:
    stmt = select(WebApplications).where(WebApplications.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_webapp_slug(slug: str, user_id: int, db: AsyncSession) -> Optional[WebApplications]:
    stmt = select(WebApplications).where(
        WebApplications.slug == slug, 
        WebApplications.user_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def delete_webapp(slug: str, db: AsyncSession) -> bool:
    stmt = select(WebApplications).where(WebApplications.slug == slug)
    result = await db.execute(stmt)
    webapp = result.scalars().first()

    if webapp:
        await db.delete(webapp)  # await shart
        await db.commit()  # await shart
        return True
    return False