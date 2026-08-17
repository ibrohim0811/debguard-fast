import os
from fastapi import APIRouter, Depends, status, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from crud.webapp import get_webapp_slug
from crud.payment import get_last_scan, transaction_create, get_my_transactions, get_my_transaction, get_transaction_webapp, get_last_successful_transaction
from core.deps import get_current_user
from schemas.payment import CheckPaymentSchema, TransactionSchema
from models import TransactionStatus, Users
from dotenv import load_dotenv
from database import AsyncSession

router = APIRouter(tags=["payment"])
load_dotenv()

@router.post("/check-payment")
async def check_payment(
    data: CheckPaymentSchema, 
    db: AsyncSession = Depends(get_db), 
    user: Users = Depends(get_current_user)
):
    webapp = await get_webapp_slug(data.slug, user_id=user.id, db=db)
    if not webapp:
        return {"message": "Veb sahifa topilmadi", "status": status.HTTP_404_NOT_FOUND}

    if not webapp.is_verified:
        return {"message": "Veb sahifangiz tasdiqdan o'tmagan!", "status": status.HTTP_406_NOT_ACCEPTABLE}

    # 1. Bepul muddatni tekshirish (2 kun ichida)
    last_scan = await get_last_scan(webapp_id=webapp.id, db=db)
    is_free_period = False

    if last_scan and last_scan.scanned_at:
        now = datetime.now(timezone.utc)
        vaqt_farqi = now - last_scan.scanned_at
        if vaqt_farqi <= timedelta(days=2):
            is_free_period = True

    # 2. To'lov holatini tekshirish (Masalan: Muvaffaqiyatli to'lov qilinganmi?)
    last_payment = await get_last_successful_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    is_paid = last_payment is not None and last_payment.status == TransactionStatus.SUCCESS

    # 3. Agar bepul muddatda bo'lsa YOKI to'lov qilingan bo'lsa -> Ruxsat beriladi
    if is_free_period or is_paid:
        return {
            "access": True,
            "message": "Skanerlash uchun ruxsat berildi."
        }

    # 4. Aks holda -> Yangi to'lov cheki yaratiladi
    transaction = await transaction_create(
        webapp_id=webapp.id,
        user_id=user.id,
        status=TransactionStatus.PENDING,
        amount=20000,
        db=db
    )
    bot_username = os.getenv("BOT_USERNAME", "DevGuardBot")
    deeplink = f"https://t.me/{bot_username}?start={transaction.payment_id}"

    return {
        "access": False,
        "message": "Skanerlash muddati tugagan. Qayta skanerlash uchun to'lov qiling.",
        "deeplink": deeplink,
        "status": status.HTTP_402_PAYMENT_REQUIRED
    }

@router.get("/my-transactions")
async def get_transactions(data: TransactionSchema, db: Session = Depends(get_db), user: Session = Depends(get_current_user)):
    try:
        transactions = await get_my_transactions(user_id=user.id, db=db)
        return transactions
    except Exception as e:
        print(e)
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Nimadur xato ketdi qaytadan urining!")
        

@router.get("/my-transaction")
async def get_transactions(data: TransactionSchema, db: Session = Depends(get_db), user: Session = Depends(get_current_user)):
    try:
        if data.payment_id is not None:
            transactions = await get_my_transaction(user_id=user.id, payment_id=data.payment_id, db=db)
            return transactions
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_id berilmagan")
    except Exception as e:
        print(e)
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Nimadur xato ketdi qaytadan urining!")


@router.get("/my-transaction")
async def get_transactions(data: TransactionSchema, db: Session = Depends(get_db), user: Session = Depends(get_current_user)):
    try:
        if data.webapp_id is not None:
            transactions = await get_transaction_webapp(user_id=user.id, webapp_id=data.webapp_id, db=db)
            return transactions
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="webapp_id berilmagan")
    except Exception as e:
        print(e)
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Nimadur xato ketdi qaytadan urining!")
        