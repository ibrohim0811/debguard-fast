from pydantic import BaseModel, EmailStr
from typing import Optional



class RegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    email: EmailStr
    password: str


class LoginSchema(BaseModel):
    phone_number: str
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# Foydalanuvchini qaytarish uchun — hashed_password bu yerda YO'Q
# Diqqat: role FAQAT o'qish uchun. RegisterSchema'da yo'q — aks holda
# har kim ro'yxatdan o'tayotib o'zini admin qilib olardi.
class UserOutSchema(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    joined_at: str



class RegisterOutSchema(BaseModel):
    user: UserOutSchema
    access_token: str
    token_type: str = "bearer"



class OtpVerifySchema(BaseModel):
    email: str
    otp: str
