import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()


# --- Konfiguratsiya (.env dan o'qiladi) ---
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_INSECURE_DEFAULT")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))


# --- Parolni hashlash ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Ochiq parolni bcrypt hashiga aylantiradi."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Kiritilgan parol saqlangan hashga mos kelishini tekshiradi."""
    return pwd_context.verify(plain, hashed)


# --- JWT token ---
def create_access_token(data: dict) -> str:
    """data (masalan {'sub': str(user_id)}) asosida imzolangan JWT yaratadi."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """Tokenni ochib, ichidagi user_id ni qaytaradi. Yaroqsiz bo'lsa None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except (JWTError, ValueError):
        return None


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_refresh_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "refresh":
            return None

        sub = payload.get("sub")

        if sub is None:
            return None

        return int(sub)

    except (JWTError, ValueError):
        return None