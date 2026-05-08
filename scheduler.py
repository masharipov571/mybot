import asyncio
import datetime
import os
from database import SessionLocal
from models import Subscription, User
from timetable_engine import get_timetable_screenshot


async def send_scheduled_timetables(bot):
    """
    Obuna bo'lgan foydalanuvchilarga belgilangan vaqtda
    dars jadvalini avtomatik yuboradi.
    
    Bu funksiya har daqiqada ishga tushadi.
    """
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")

    db = SessionLocal()
    try:
        # Hozirgi vaqtga mos obunalarni topish
        subscriptions = db.query(Subscription).filter(
            Subscription.notification_time == current_time
        ).all()

        if not subscriptions:
            db.close()
            return

        print(f"[Scheduler] {current_time}: {len(subscriptions)} ta obunachiga jadval yuborilmoqda...")

        for sub in subscriptions:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if not user:
                continue

            try:
                screenshot_path = await get_timetable_screenshot(sub.group_name)
                if screenshot_path and os.path.exists(screenshot_path):
                    from aiogram.types import FSInputFile
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=FSInputFile(screenshot_path),
                        caption=f"📅 {sub.group_name} guruhi — Bugungi dars jadvali\n🕐 {current_time}"
                    )
                    os.remove(screenshot_path)
                    print(f"[Scheduler] Sent to user {user.telegram_id}")
                else:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"⚠️ {sub.group_name} guruhi jadvali topilmadi. Guruh nomini /start orqali qayta kiriting."
                    )
            except Exception as e:
                print(f"[Scheduler] Error sending to {user.telegram_id}: {e}")

    finally:
        db.close()


async def scheduler_loop(bot):
    """Har daqiqada scheduler tekshiruvini bajaradi"""
    print("[Scheduler] Started — checking every minute...")
    while True:
        try:
            await send_scheduled_timetables(bot)
        except Exception as e:
            print(f"[Scheduler] Loop error: {e}")
        await asyncio.sleep(60)
