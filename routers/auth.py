import os
import random
import resend
import logging
import json
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool


from database import get_db
from schemas.auth import RegisterSchema, LoginSchema, TokenSchema, UserOutSchema, OtpVerifySchema
from crud.user import get_user_by_email, create_user, get_user_by_phone_number
from core.security import hash_password, verify_password, create_access_token
from core.deps import get_current_user
from models import Users

router = APIRouter(tags=["auth"])

logger = logging.getLogger(__name__)
r = redis.from_url("redis://localhost:6379", decode_responses=True)
templates = Jinja2Templates(directory="templates")


load_dotenv()


def render_email_template(full_name: str, otp_code: str) -> str:
    # 1. HTML faylni template sifatida yuklaymiz
    template = templates.get_template("email_render.html")

    # 2. Ma'lumotlarni biriktirib, HTML'ni STRING holatida render qilamiz
    html_content = template.render(
        full_name=full_name,
        otp_code=otp_code
    )

    return html_content


@router.post("/register")
async def register(data: RegisterSchema, db: Session = Depends(get_db)):

    if get_user_by_phone_number(data.phone_number, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan"
        )
    
    # 1. Email band emasligini tekshirish
    if get_user_by_email(data.email, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email allaqachon ro'yxatdan o'tgan",
        )

    otp_code = str(random.randint(100000, 999999))

    user_data = {
        "full_name":data.full_name,
        "email":data.email,
        "phone_number":data.phone_number,
        "password":hash_password(data.password),
    }

    await r.set(f"user:{data.email}", json.dumps(user_data), ex=350)
    await r.set(f"otp:{data.email}", otp_code, ex=350)

    api_key = os.getenv("RESEND_API_KEY")
    resend.api_key = api_key
    
    try:
        logger.info(f"malumot tayyor {user_data}, token:{api_key}")
        html = render_email_template(data.full_name, otp_code)
        subject = f"{otp_code} - Devguard Tasdiqlash kodi"

        await run_in_threadpool(
            resend.Emails.send,
            {
                "from": "DevGuard <no-reply@devguard.uz>",
                "to": [data.email],
                "subject": subject,
                "html": html
            }
        )

        return {"message":"Emailga 6 xonali kod yuborildi", "status":status.HTTP_200_OK}
    except Exception as e:
        logger.info(f"SMTP XATO:{e}")
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nimadur xato ketdi!")


@router.post("/confirm-registration")
async def confirm_registration(data: OtpVerifySchema, db: Session = Depends(get_db)):
    
    otp_code = await r.get(f"otp:{data.email}")
    
    if isinstance(otp_code, bytes):
        otp_code = otp_code.decode("utf-8")

    if not otp_code or otp_code != str(data.otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="OTP kod noto'g'ri yoki muddati tugagan!"
        )

    raw_user_data = await r.get(f"user:{data.email}")
    if not raw_user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Foydalanuvchi ma'lumotlari topilmadi yoki muddati o'tgan!"
        )

    try:
        user_data = json.loads(raw_user_data)

        user = create_user(
            full_name=user_data["full_name"],
            email=user_data["email"],
            phone_number=user_data["phone_number"],
            password=user_data["password"], 
            db=db,
        )

        await r.delete(f"otp:{data.email}")
        await r.delete(f"user:{data.email}")

        token = create_access_token({"sub": str(user.id)})

        return {
            "user": user, 
            "access_token": token, 
            "token_type": "bearer"
        }

    except Exception as e:
        logger.error(f"CONFIRM SAQLASHDA XATO: {e}")
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Nimadir xato ketdi, qaytadan urining!"
        )


@router.post("/login", response_model=TokenSchema)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = get_user_by_phone_number(data.phone_number, db)

    # user yo'q YOKI parol noto'g'ri — bir xil 401 (user enumeration'dan himoya)
    if not user or not user.password or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon raqam yoki parol noto'g'ri",
        )

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOutSchema)
def me(current_user: Users = Depends(get_current_user)):
    """Joriy (tokenli) foydalanuvchi ma'lumotlari."""
    return current_user



