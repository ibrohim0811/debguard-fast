import os
import asyncio
import logging
from pathlib import Path

from celery_app import celery_app
from utils.ai import analyze_logs_with_groq, clean_and_truncate_log
from aiogram import Bot

BASE_DIR = Path(__file__).resolve().parent.parent
BOT_TOKEN = os.getenv("BOT_TOKEN")

logger = logging.getLogger(__name__)

async def _send_bot_message(chat_id: int, text: str):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    finally:
        await bot.session.close()

async def _execute_script(script_path: str, domain: str, timeout: int = 600):
    process = await asyncio.create_subprocess_exec(
        script_path, domain,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout_lines = []
    stderr_lines = []

    async def read_stdout():
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded = line.decode('utf-8', errors='ignore').strip()
            if decoded:
                logger.info(f"⚙️ [WORKER LIVE]: {decoded}")
                stdout_lines.append(decoded)

    async def read_stderr():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            decoded = line.decode('utf-8', errors='ignore').strip()
            if decoded:
                logger.error(f"⚠️ [WORKER ERROR]: {decoded}")
                stderr_lines.append(decoded)

    try:
        await asyncio.wait_for(
            asyncio.gather(read_stdout(), read_stderr(), process.wait()),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return False, "", "Timeout: Skanerlash uzoq davom etdi", -1

    return True, "\n".join(stdout_lines), "\n".join(stderr_lines), process.returncode


@celery_app.task(name="tasks.run_background_scan")
def run_background_scan(script_name: str, domain: str, telegram_id: int, user_full_name: str, webapp_title: str):
    """Celery Worker ichida ishlovchi fonaviy skanerlash vazifasi"""
    script_path = str(BASE_DIR / "routers" / script_name)
    
    # 1. Navbatga tushgani haqida xabar yuborish
    asyncio.run(_send_bot_message(
        telegram_id, 
        f"Hurmatli {user_full_name}!\nSizning {webapp_title} nomli projectingiz skanerlash navbatiga qo'yildi ⌛"
    ))

    # 2. Skriptni bajarish (10 daqiqa timeout bilan)
    success, stdout_text, stderr_text, returncode = asyncio.run(
        _execute_script(script_path, domain, timeout=600)
    )

    if not success:
        asyncio.run(_send_bot_message(
            telegram_id, 
            "⚠️ Skanerlash juda uzoq davom etgani sababli to'xtatildi (Timeout)!"
        ))
        return {"status": "timeout"}

    if returncode == 0:
        asyncio.run(_send_bot_message(
            telegram_id, 
            f"{user_full_name} projectingiz skanerlanib bo'lindi ⏰!\nUni RON AI Assistant ko'rib chiqmoqda 👀..."
        ))

        # AI tahlil
        cleaned_log = clean_and_truncate_log(stdout_text)
        ai_summary = asyncio.run(analyze_logs_with_groq(cleaned_log))

        # Yakuniy natijani bot orqali yuborish
        asyncio.run(_send_bot_message(
            telegram_id, 
            f"RON AI Assistant ✨ yakuniy xulosa qildi\n\nRonning xulosasi:\n{ai_summary}\n\nSkanerlash muvaffaqiyatli yakunlandi 🎉"
        ))

        return {"status": "success", "result": ai_summary}
    else:
        asyncio.run(_send_bot_message(
            telegram_id, 
            "Skanerlash jarayonida xatolik yuzaga keldi !"
        ))
        return {"status": "failed", "error": stderr_text}