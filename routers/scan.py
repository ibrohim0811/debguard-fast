import os
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.deps import get_current_user
from schemas.scan import ScanCreateSchema
from models import TransactionStatus, Users
from crud.webapp import get_webapp_slug
from crud.payment import (
    get_last_scan, 
    transaction_create, 
    get_last_successful_transaction, 
    get_pending_transaction
)
from utils.tasks import run_background_scan

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["scan"])

@router.post("/scan-web/audit")
async def scan_web_audit(
    data: ScanCreateSchema, 
    db: AsyncSession = Depends(get_db), 
    user: Users = Depends(get_current_user)
):
    webapp = await get_webapp_slug(slug=data.slug, user_id=user.id, db=db)
    if not webapp:
        return {"message": "Veb sahifa topilmadi", "status": status.HTTP_404_NOT_FOUND}

    if not webapp.is_verified:
        return {"message": "Veb sahifangiz tasdiqdan o'tmagan!", "status": status.HTTP_406_NOT_ACCEPTABLE}

    # Bepul muddat va to'lov tekshiruvi
    last_scan = await get_last_scan(webapp_id=webapp.id, db=db)
    is_free_period = False
    if last_scan and last_scan.scanned_at:
        if datetime.now(timezone.utc) - last_scan.scanned_at <= timedelta(days=2):
            is_free_period = True

    last_payment = await get_last_successful_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    is_paid = last_payment is not None

    if is_free_period or is_paid:
        # CELERY TASK'NI NAVBATGA QO'SHISH (API darhol javob qaytaradi)
        task = run_background_scan.delay(
            script_name="full-scan.sh",
            domain=webapp.domain,
            telegram_id=user.telegram_id,
            user_full_name=user.full_name,
            webapp_title=webapp.title
        )

        logger.info(f"🚀 [AUDIT] Task Celery navbatiga qo'shildi. Task ID: {task.id}")

        return {
            "access": True, 
            "message": "Skanerlash navbatga qo'shildi. Natija Telegram orqali yuboriladi.",
            "task_id": task.id
        }

    # To'lov talab qilinishi
    pending_transaction = await get_pending_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    transaction = pending_transaction or await transaction_create(
        webapp_id=webapp.id, user_id=user.id, status=TransactionStatus.PENDING, amount=20000, db=db
    )

    bot_username = os.getenv("BOT_USERNAME", "DevGuardBot")
    return {
        "access": False,
        "message": "Skanerlash muddati tugagan. Qayta skanerlash uchun to'lov qiling.",
        "deeplink": f"https://t.me/{bot_username}?start={transaction.payment_id}",
        "status": status.HTTP_402_PAYMENT_REQUIRED
    }


@router.post("/scan-web/ddos")
async def scan_web_ddos(
    data: ScanCreateSchema, 
    db: AsyncSession = Depends(get_db), 
    user: Users = Depends(get_current_user)
):
    webapp = await get_webapp_slug(slug=data.slug, user_id=user.id, db=db)
    if not webapp:
        return {"message": "Veb sahifa topilmadi", "status": status.HTTP_404_NOT_FOUND}

    if not webapp.is_verified:
        return {"message": "Veb sahifangiz tasdiqdan o'tmagan!", "status": status.HTTP_406_NOT_ACCEPTABLE}

    # Bepul muddat va to'lov tekshiruvi
    last_scan = await get_last_scan(webapp_id=webapp.id, db=db)
    is_free_period = False
    if last_scan and last_scan.scanned_at:
        if datetime.now(timezone.utc) - last_scan.scanned_at <= timedelta(days=2):
            is_free_period = True

    last_payment = await get_last_successful_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    is_paid = last_payment is not None

    if is_free_period or is_paid:
        # CELERY TASK'NI NAVBATGA QO'SHISH (API darhol javob qaytaradi)
        task = run_background_scan.delay(
            script_name="ddos.sh",
            domain=webapp.domain,
            telegram_id=user.telegram_id,
            user_full_name=user.full_name,
            webapp_title=webapp.title
        )

        logger.info(f"🚀 [AUDIT] Task Celery navbatiga qo'shildi. Task ID: {task.id}")

        return {
            "access": True, 
            "message": "Skanerlash navbatga qo'shildi. Natija Telegram orqali yuboriladi.",
            "task_id": task.id
        }

    # To'lov talab qilinishi
    pending_transaction = await get_pending_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    transaction = pending_transaction or await transaction_create(
        webapp_id=webapp.id, user_id=user.id, status=TransactionStatus.PENDING, amount=20000, db=db
    )

    bot_username = os.getenv("BOT_USERNAME", "DevGuardBot")
    return {
        "access": False,
        "message": "Skanerlash muddati tugagan. Qayta skanerlash uchun to'lov qiling.",
        "deeplink": f"https://t.me/{bot_username}?start={transaction.payment_id}",
        "status": status.HTTP_402_PAYMENT_REQUIRED
    }