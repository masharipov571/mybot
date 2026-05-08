import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo, FSInputFile
)
from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from models import User, Subscription
from timetable_engine import get_timetable_screenshot

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# ─── Sozlamalar ────────────────────────────────────────────────────────────────
TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")

if not TOKEN:
    logger.critical(f"❌ BOT_TOKEN topilmadi! Hozirgi qiymat: '{TOKEN}'")
    raise SystemExit(1)

if not WEBAPP_URL:
    logger.warning("⚠️ WEBAPP_URL topilmadi! WebApp ishlashi uchun Railway > Variables ga qo'shing.")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ─── FSM Holatlari ─────────────────────────────────────────────────────────────
class TimetableForm(StatesGroup):
    waiting_for_group = State()


class SubscribeForm(StatesGroup):
    waiting_for_group = State()
    waiting_for_time = State()


# ─── Yordamchi funksiyalar ─────────────────────────────────────────────────────
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari"""
    buttons = [
        [KeyboardButton(
            text="📚 Quiz WebApp",
            web_app=WebAppInfo(url=WEBAPP_URL) if WEBAPP_URL else None
        )],
        [
            KeyboardButton(text="📅 Dars Jadvali"),
            KeyboardButton(text="🔔 Obuna Bo'lish")
        ],
        [KeyboardButton(text="❌ Obunani Bekor Qilish")]
    ]
    # WEBAPP_URL yo'q bo'lsa, oddiy tugma
    if not WEBAPP_URL:
        buttons[0] = [KeyboardButton(text="📚 Quiz")]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def save_user(telegram_id: int, first_name: str, username: str = None):
    """Foydalanuvchini bazaga saqlash yoki yangilash"""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username
            )
            db.add(user)
            db.commit()
            logger.info(f"New user saved: {telegram_id} ({first_name})")
    finally:
        db.close()


# ─── Handlerlar ────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Boshlash buyrug'i"""
    await state.clear()  # Eski holatni tozalash

    save_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )

    await message.answer(
        f"👋 Assalomu alaykum, <b>{message.from_user.first_name}</b>!\n\n"
        f"🎓 <b>TSUE Study Assistant</b> botiga xush kelibsiz.\n\n"
        f"📚 Bu bot orqali:\n"
        f"• Quiz testlarini ishlashingiz\n"
        f"• Dars jadvalingizni ko'rishingiz\n"
        f"• Kundalik jadval xabarnomalariga obuna bo'lishingiz mumkin!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Yordam"""
    await message.answer(
        "📋 <b>Buyruqlar:</b>\n\n"
        "/start — Botni qayta ishga tushirish\n"
        "/help — Ushbu xabar\n\n"
        "🔘 <b>Tugmalar:</b>\n\n"
        "📚 <b>Quiz WebApp</b> — Testlarni ishlash platformasi\n"
        "📅 <b>Dars Jadvali</b> — Guruhingiz jadvalini ko'rish\n"
        "🔔 <b>Obuna Bo'lish</b> — Kundalik jadval xabarnomasi\n"
        "❌ <b>Obunani Bekor Qilish</b> — Xabarnomalarni to'xtatish",
        parse_mode="HTML"
    )


# ─── Dars Jadvali ──────────────────────────────────────────────────────────────

@dp.message(F.text == "📅 Dars Jadvali")
async def ask_group_for_timetable(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📅 <b>Dars Jadvalini Ko'rish</b>\n\n"
        "Guruh nomini kiriting.\n"
        "Masalan: <code>II-53/24</code>",
        parse_mode="HTML"
    )
    await state.set_state(TimetableForm.waiting_for_group)


@dp.message(TimetableForm.waiting_for_group)
async def send_timetable(message: types.Message, state: FSMContext):
    group = message.text.strip()
    await state.clear()

    wait_msg = await message.answer(
        f"⏳ <b>{group}</b> guruhi jadvalini tayyorlamoqdaman...\n"
        f"Bir oz kuting (10-20 sekund)",
        parse_mode="HTML"
    )

    screenshot_path = await get_timetable_screenshot(group)

    try:
        await wait_msg.delete()
    except Exception:
        pass

    if screenshot_path and os.path.exists(screenshot_path):
        await message.answer_photo(
            photo=FSInputFile(screenshot_path),
            caption=f"📅 <b>{group}</b> guruhi — Haftalik dars jadvali",
            parse_mode="HTML"
        )
        try:
            os.remove(screenshot_path)
        except Exception:
            pass
    else:
        await message.answer(
            f"❌ <b>{group}</b> guruhi jadvali topilmadi.\n\n"
            f"Guruh nomini to'g'ri formatda kiriting:\n"
            f"Masalan: <code>II-53/24</code>",
            parse_mode="HTML"
        )


# ─── Obuna ─────────────────────────────────────────────────────────────────────

@dp.message(F.text == "🔔 Obuna Bo'lish")
async def ask_group_for_subscribe(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔔 <b>Kundalik Jadval Obunasi</b>\n\n"
        "Obuna bo'lish uchun guruh nomini kiriting.\n"
        "Masalan: <code>II-53/24</code>",
        parse_mode="HTML"
    )
    await state.set_state(SubscribeForm.waiting_for_group)


@dp.message(SubscribeForm.waiting_for_group)
async def ask_time_for_subscribe(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text.strip())
    await message.answer(
        "🕐 <b>Xabar kelish vaqtini kiriting</b>\n\n"
        "Har kuni soat nechada jadval kelsin?\n"
        "Format: <code>08:00</code>\n\n"
        "Masalan: <code>07:30</code> yoki <code>18:00</code>",
        parse_mode="HTML"
    )
    await state.set_state(SubscribeForm.waiting_for_time)


@dp.message(SubscribeForm.waiting_for_time)
async def save_subscription(message: types.Message, state: FSMContext):
    time_text = message.text.strip()

    # Vaqt formatini tekshirish
    try:
        hour, minute = time_text.split(":")
        assert 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59
        time_text = f"{int(hour):02d}:{int(minute):02d}"
    except Exception:
        await message.answer(
            "❌ Vaqt formati noto'g'ri! \n"
            "Iltimos <code>HH:MM</code> formatida kiriting.\n"
            "Masalan: <code>08:00</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    group = data.get("group", "")
    await state.clear()

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user:
            sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            if sub:
                sub.group_name = group
                sub.notification_time = time_text
            else:
                sub = Subscription(user_id=user.id, group_name=group, notification_time=time_text)
                db.add(sub)
            db.commit()
    finally:
        db.close()

    await message.answer(
        f"✅ <b>Obuna muvaffaqiyatli!</b>\n\n"
        f"📚 Guruh: <b>{group}</b>\n"
        f"🕐 Vaqt: <b>Har kuni soat {time_text}</b>\n\n"
        f"Endi har kuni belgilangan vaqtda dars jadvalingiz avtomatik yuboriladi.",
        parse_mode="HTML"
    )


@dp.message(F.text == "❌ Obunani Bekor Qilish")
async def cancel_subscription(message: types.Message, state: FSMContext):
    await state.clear()
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user:
            sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            if sub:
                db.delete(sub)
                db.commit()
                await message.answer(
                    "✅ Obuna bekor qilindi.\n"
                    "Endi jadval xabarnomalar kelmaydi."
                )
            else:
                await message.answer("ℹ️ Siz hozirda hech qanday obunaga ega emassiz.")
        else:
            await message.answer("ℹ️ Siz hozirda hech qanday obunaga ega emassiz.")
    finally:
        db.close()


# ─── Bot ishga tushirish ───────────────────────────────────────────────────────

async def run_bot():
    """Botni ishga tushirish"""
    init_db()
    logger.info("✅ Bot polling boshlanmoqda...")

    # Schedulerni parallel ishga tushirish
    from scheduler import scheduler_loop
    asyncio.create_task(scheduler_loop(bot))

    # WebApp menyu tugmasini o'rnatish ("Open" tugmasi)
    try:
        from aiogram.types import MenuButtonWebApp, WebAppInfo
        if WEBAPP_URL:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Open",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            )
            logger.info("✅ WebApp Menu Button ('Open') o'rnatildi")
    except Exception as e:
        logger.error(f"❌ Menu button o'rnatishda xato: {e}")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
