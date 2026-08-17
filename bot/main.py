import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# SQLAlchemy importlari
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import TransactionHistory, Users, TransactionStatus  # Modellaringiz
from bot.states import PaymentState
from bot.button import sorov, back_web
from database import get_db_context  # Yuqoridagi session helper

load_dotenv()

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

BANK_CARD = os.getenv("CREDIT_CARD")
CARD_OWNER = os.getenv("CARD_OWNER")
ADMIN_ID = os.getenv("ADMIN_ID")


@dp.message(Command('start'))
async def start(msg: types.Message, state: FSMContext, command: CommandObject):
    args = command.args

    if not args:
        await msg.answer(
            f"Assalomu alaykum {msg.from_user.first_name}! "
            f"Vebsaytni scan qilish uchun https://devshield.uz orqali amalga oshiring!"
        )
        return

    payment_id = args

    async with get_db_context() as db:
        # SQLAlchemy selectinload: TransactionHistory bilan birga User'ni ham yuklab oladi (Django select_related kabi)
        stmt = (
            select(TransactionHistory)
            .options(selectinload(TransactionHistory.user))
            .where(TransactionHistory.payment_id == payment_id)
        )
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()

        if not tx:
            await msg.answer("Xato to'lov havolasi! ❌")
            return

        # Foydalanuvchi Telegram ID-sini yangilash
        try:
            if tx.user and tx.user.telegram_id != msg.from_user.id:
                tx.user.telegram_id = msg.from_user.id
                await db.commit()
        except IntegrityError:
            await db.rollback()

        # Vaqtincha tekshirish (1 soatlik muddat)
        # timezone.utc yoki mahalliy vaqt mosligiga e'tibor bering
        now = datetime.now(timezone.utc) if tx.payment_date.tzinfo else datetime.now()
        
        if now - tx.payment_date > timedelta(hours=1):
            await msg.answer(
                "Ushbu to'lov havolasining muddati tugagan (1 soat). "
                "Iltimos, qaytadan yangi to'lov so'rovi yarating! ⚠️"
            )
            tx.status = TransactionStatus.TIMEOUT  # Yoki sizdagi status enum/str nomi
            await db.commit()
            return

        # To'lov holatini tekshirish
        if tx.status == TransactionStatus.SUCCESS:
            await msg.answer("Bu to'lov avval amalga oshirilgan 🎉")
            return

        # To'lov ma'lumotlarini yuborish
        await msg.answer(
            f"Skanerlash xizmati narxi: 20,000 so'm.\n\n"
            f"💳 Karta raqam: <b><code>{BANK_CARD}</code></b> ({CARD_OWNER})\n\n"
            f"Iltimos, to'lovni amalga oshirib, chek (rasm) variantini shu yerga yuboring.\n",
            parse_mode="HTML"
        )

        # State-ni saqlash
        await state.update_data(
            payment_id=payment_id,
            user_chat_id=msg.from_user.id,
            username=msg.from_user.username,
            user_phone=tx.user.phone_number if tx.user else "Kiritilmagan"
        )
        await state.set_state(PaymentState.payment_cheque)


@dp.message(F.photo, PaymentState.payment_cheque)
async def get_cheque(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    username = data.get("username") or msg.from_user.username or "Mavjud emas"
    user_phone = data.get("user_phone") or "Kiritilmagan"
    formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Adminga yuborish
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=msg.photo[-1].file_id,
        caption=(
            f"💰 <b>Yangi to'lov so'rovi!</b>\n\n"
            f"👤 Foydalanuvchi: @{username}\n"
            f"📞 Telefon: {user_phone}\n"
            f"💵 Summa: 20 000 UZS\n"
            f"🕰️ To'lov vaqti: {formatted_time}"
        ),
        parse_mode="HTML",
        reply_markup=sorov(payment_id=payment_id)
    )
    await msg.answer("Rahmat! To'lovingiz tekshirish uchun adminga yuborildi. ⏳")
    await state.clear()


@dp.callback_query(F.data.startswith("accept_") | F.data.startswith("decline_"))
async def yes_or_no(callback: types.CallbackQuery):
    action, payment_id = callback.data.split("_", 1)

    async with get_db_context() as db:
        stmt = (
            select(TransactionHistory)
            .options(selectinload(TransactionHistory.user))
            .where(TransactionHistory.payment_id == payment_id)
        )
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()

        if not tx:
            await callback.answer("Tranzaksiya topilmadi yoki o'chib ketgan!", show_alert=True)
            return

        target_chat_id = tx.user.telegram_id if tx.user else None

        if not target_chat_id:
            await callback.answer("Foydalanuvchining Telegram ID si topilmadi! Baza yangilanmagan.", show_alert=True)
            return

        if action == "accept":
            tx.status = TransactionStatus.SUCCESS
            await db.commit()
            print("SAQLANDI SUCCESS")

            try:
                await bot.send_message(
                    chat_id=target_chat_id,
                    text="To'lovingiz muvaffaqiyatli qabul qilindi! Saytni qayta skan qilishingiz mumkin. ✅",
                    reply_markup=back_web()
                )
            except Exception as e:
                logging.error(f"Xabar yuborishda xatolik: {e}")

            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\n✅ <b>ADMIN TASDIQLADI</b>",
                parse_mode="HTML"
            )

        elif action == "decline":
            tx.status = TransactionStatus.DECLINED
            await db.commit()
            print("SAQLANDI DECLINE")

            try:
                await bot.send_message(
                    chat_id=target_chat_id,
                    text="Siz yuborgan to'lov cheki admin tomonidan rad etildi! Iltimos qayta tekshirib yuboring. ❌"
                )
            except Exception as e:
                logging.error(f"Xabar yuborishda xatolik: {e}")

            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\n\n❌ <b>ADMIN RAD ETDI</b>",
                parse_mode="HTML"
            )

async def send_real_time_scan(chat_id, text, bot: Bot):
    await bot.send_message(chat_id=chat_id, text=text)

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())