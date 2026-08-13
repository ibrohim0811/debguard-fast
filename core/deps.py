import jwt
import os
from fastapi import Depends, HTTPException, status, WebSocket, WebSocketException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.core.security import decode_access_token
from backend.models import Users
from dotenv import load_dotenv

load_dotenv()

# Swagger UI dagi "Authorize" tugmasi shu tokenUrl ga qarab ishlaydi
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_INSECURE_DEFAULT")
ALGORITHM = "HS256"

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Users:
    """Authorization: Bearer <token> ni tekshirib, joriy foydalanuvchini qaytaradi."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Yaroqsiz yoki muddati o'tgan token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user

async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        user = db.query(Users).filter(Users.id == int(user_id)).first()
        return user
    except Exception:
        return None