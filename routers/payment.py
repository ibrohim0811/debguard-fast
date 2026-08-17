import os
from fastapi import APIRouter, Depends, status
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from crud.webapp import get_webapp_slug
from crud.payment import get_last_scan, transaction_create
from core.deps import get_current_user
from schemas.payment import CheckPaymentSchema
from models import TransactionStatus
from dotenv import load_dotenv

router = APIRouter(tags=["payment"])
load_dotenv()

@router.post("/check-payment")
async def check_payment(data: CheckPaymentSchema, db: Session = Depends(get_db), user: Session = Depends(get_current_user)):
    webapp = await get_webapp_slug(data.slug, user_id=user.id, db=db)
    if webapp:
        if webapp.is_verified:
            last_scan = await get_last_scan(webapp_id=webapp.id, db=db)
            if last_scan and last_scan.scanned_at:
                now = datetime.now(timezone.utc)
                vaqt_farqi = now - last_scan.scanned_at
                if vaqt_farqi <= timedelta(days=2):
                    return {
                        "access": True,
                        "message": "Skanerlash uchun ruxsat berildi."
                    }
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
                "status":status.HTTP_402_PAYMENT_REQUIRED
            }

        return {"message":"Veb sahifangiz tasdiqdan o'tmagan!", "status": status.HTTP_406_NOT_ACCEPTABLE}
    return {"message":"Veb sahifa topilmadi", "status":status.HTTP_404_NOT_FOUND}


