import os
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database import get_db
from core.deps import get_current_user
from schemas.scan import ScanCreateSchema
from models import ScanType, TransactionStatus, Users
from crud.webapp import get_webapp_slug
from crud.payment import (
    get_last_scan, 
    transaction_create, 
    get_last_successful_transaction, 
    get_pending_transaction
)
from crud.scan import create_scan_history
from utils.ai import analyze_logs_with_groq, clean_and_truncate_log

load_dotenv()

router = APIRouter(tags=["scan"])
BOT_TOKEN=os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

@router.post("/scan-web/audit")
async def scan_web_audit(
    data: ScanCreateSchema, 
    db: AsyncSession = Depends(get_db), 
    user: Users = Depends(get_current_user)
):
    # 1. Veb-ilovani tekshirish
    webapp = await get_webapp_slug(slug=data.slug, user_id=user.id, db=db)
    if not webapp:
        return {"message": "Veb sahifa topilmadi", "status": status.HTTP_404_NOT_FOUND}

    if not webapp.is_verified:
        return {"message": "Veb sahifangiz tasdiqdan o'tmagan!", "status": status.HTTP_406_NOT_ACCEPTABLE}

    # 2. Bepul foydalanish muddatini tekshirish (2 kun ichida)
    last_scan = await get_last_scan(webapp_id=webapp.id, db=db)
    is_free_period = False

    if last_scan and last_scan.scanned_at:
        now = datetime.now(timezone.utc)
        vaqt_farqi = now - last_scan.scanned_at
        if vaqt_farqi <= timedelta(days=2):
            is_free_period = True

    # 3. Muvaffaqiyatli to'lov qilingan-qilinmaganini tekshirish
    last_payment = await get_last_successful_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    is_paid = last_payment is not None

    # 4. Bepul muddatda bo'lsa YOKI To'lov qilingan bo'lsa -> Skanerlashni bajarish
    if is_free_period or is_paid:
        from bot.main import send_real_time_scan

        script_path = str(BASE_DIR / "routers" / "full-scan.sh")
        process = await asyncio.create_subprocess_exec(
            script_path, webapp.domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        chat_id = user.telegram_id
        await send_real_time_scan(
            chat_id, 
            f"Hurmatli {user.full_name}!\nSizning {webapp.title} nomli projectingiz to'liq skanerlash navbatiga qo'yildi ⌛",
            bot=bot
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            scan_result = stdout.decode().strip()

            await send_real_time_scan(
                chat_id, 
                f"{user.full_name} projectingiz Auditi tugadi ⏰ !\nUni RON AI Assistant ko'rib chiqmoqda 👀...",
                bot=bot
            )

            r = await analyze_logs_with_groq(clean_and_truncate_log(scan_result))

            await create_scan_history(
                webapp_id=webapp.id,
                result_summary=r,
                scan_type=ScanType.FULL_SCAN,
                db=db
            )

            await send_real_time_scan(
                chat_id, 
                f"RON AI Assistant ✨ yakuniy xulosa qildi\nRonning xulosasi: {r}\nSkanerlash muvaffaqiyatli yakunlandi 🎉",
                bot=bot
            )

            return {"access": True, "message": "Skanerlash muvaffaqiyatli yakunlandi", "result": r}
        else:
            print(stderr)
            await send_real_time_scan(chat_id, "Skanerlash jarayonida xatolik yuzaga keldi !", bot=bot)
            return {"message": "Skanerlashda xatolik", "status": status.HTTP_502_BAD_GATEWAY}

    # 5. Aks holda -> PENDING tranzaksiyani olish yoki yangisini yaratish
    pending_transaction = await get_pending_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    if pending_transaction:
        transaction = pending_transaction
    else:
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


@router.post("/scan-web/ddos")
async def scan_web_ddos(
    data: ScanCreateSchema, 
    db: AsyncSession = Depends(get_db), 
    user: Users = Depends(get_current_user)
):
    # 1. Veb-ilovani tekshirish
    webapp = await get_webapp_slug(slug=data.slug, user_id=user.id, db=db)
    if not webapp:
        return {"message": "Veb sahifa topilmadi", "status": status.HTTP_404_NOT_FOUND}

    if not webapp.is_verified:
        return {"message": "Veb sahifangiz tasdiqdan o'tmagan!", "status": status.HTTP_406_NOT_ACCEPTABLE}

    # 2. Bepul foydalanish muddatini tekshirish (2 kun ichida)
    last_scan = await get_last_scan(webapp_id=webapp.id, db=db)
    is_free_period = False

    if last_scan and last_scan.scanned_at:
        now = datetime.now(timezone.utc)
        vaqt_farqi = now - last_scan.scanned_at
        if vaqt_farqi <= timedelta(days=2):
            is_free_period = True

    # 3. Muvaffaqiyatli to'lov qilingan-qilinmaganini tekshirish
    last_payment = await get_last_successful_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    is_paid = last_payment is not None

    # 4. Bepul muddatda bo'lsa YOKI To'lov qilingan bo'lsa -> Skanerlashni bajarish
    if is_free_period or is_paid:
        from bot.main import send_real_time_scan

        script_path = str(BASE_DIR / "routers" / "ddos.sh")
        process = await asyncio.create_subprocess_exec(
            script_path, webapp.domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        chat_id = user.telegram_id
        await send_real_time_scan(
            chat_id, 
            f"Hurmatli {user.full_name}!\nSizning {webapp.title} nomli projectingiz DDoS skanerlash navbatiga qo'yildi ⌛",
            bot=bot
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            scan_result = stdout.decode().strip()

            await send_real_time_scan(
                chat_id, 
                f"{user.full_name} projectingiz DDoS testi tugadi ⏰ !\nUni RON AI Assistant ko'rib chiqmoqda 👀...",
                bot=bot
            )

            r = await analyze_logs_with_groq(clean_and_truncate_log(scan_result))

            await create_scan_history(
                webapp_id=webapp.id,
                result_summary=r,
                scan_type=ScanType.DDOS,
                db=db
            )

            await send_real_time_scan(
                chat_id, 
                f"RON AI Assistant ✨ yakuniy xulosa qildi\nRonning xulosasi: {r}\nSkanerlash muvaffaqiyatli yakunlandi 🎉",
                bot=bot
            )

            return {"access": True, "message": "Skanerlash muvaffaqiyatli yakunlandi", "result": r}
        else:
            print(stderr)
            await send_real_time_scan(chat_id, "Skanerlash jarayonida xatolik yuzaga keldi !", bot=bot)
            return {"message": "Skanerlashda xatolik", "status": status.HTTP_502_BAD_GATEWAY}

    # 5. Aks holda -> PENDING tranzaksiyani olish yoki yangisini yaratish
    pending_transaction = await get_pending_transaction(webapp_id=webapp.id, user_id=user.id, db=db)
    if pending_transaction:
        transaction = pending_transaction
    else:
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