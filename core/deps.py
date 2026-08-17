import jwt
import os
from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.security import decode_access_token
from models import Users
from dotenv import load_dotenv

load_dotenv()

# Swagger UI dagi "Authorize" tugmasi uchun
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_INSECURE_DEFAULT")
ALGORITHM = "HS256"


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Users:
    """Authorization: Bearer <token> ni tekshirib, joriy foydalanuvchini qaytaradi."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Yaroqsiz yoki muddati o'tgan token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Token orqali user_id ni olish
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    # Asinxron bazadan foydalanuvchini qidirish
    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[Users]:
    """WebSocket ulanishi uchun tokenni tekshirish va foydalanuvchini qaytarish."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        # Asinxron bazadan foydalanuvchini qidirish
        stmt = select(Users).where(Users.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalars().first()
        return user
    except Exception:
        return None