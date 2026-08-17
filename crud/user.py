from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Users


async def get_user_by_email(email: str, db: AsyncSession) -> Optional[Users]:
    """Email bo'yicha foydalanuvchini qaytaradi (yoki None)."""
    stmt = select(Users).where(Users.email == email)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_phone_number(phone_number: str, db: AsyncSession) -> Optional[Users]:
    """Telefon raqami bo'yicha foydalanuvchini qaytaradi (yoki None)."""
    stmt = select(Users).where(Users.phone_number == phone_number)
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_user(full_name: str, phone_number: str, email: str, password: str, db: AsyncSession) -> Users:
    """Yangi foydalanuvchi yaratadi."""
    new_user = Users(
        full_name=full_name,
        phone_number=phone_number,
        email=email,
        password=password
    )
    db.add(new_user)  # await shart emas
    await db.commit()  # await shart
    await db.refresh(new_user)  # await shart
    return new_user