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

class AdminBroadcast(StatesGroup):
    waiting_for_message = State()
    waiting_for_button = State()

# ─── Yordamchi funksiyalar ─────────────────────────────────────────────────────
def get_main_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
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
    
    # Admin tekshiruvi
    from api import is_admin
    if user_id and is_admin(str(user_id)):
        buttons.append([KeyboardButton(text="📢 Xabar yuborish")])

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
        f"🎓 <b>TSUE Study Assistant</b> botiga xush kelibsiz.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

# ─── Admin Broadcast ───────────────────────────────────────────────────────────

@dp.message(lambda m: m.text == "📢 Xabar yuborish")
async def broadcast_start(message: types.Message, state: FSMContext):
    from api import is_admin
    if not is_admin(str(message.from_user.id)):
        return
    
    await state.set_state(AdminBroadcast.waiting_for_message)
    await message.answer(
        "📝 <b>Xabarni yuboring.</b>\n\nBu matn, rasm yoki video bo'lishi mumkin. Bot uni barcha foydalanuvchilarga tarqatadi.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        )
    )

@dp.message(AdminBroadcast.waiting_for_message)
async def broadcast_receive_msg(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=get_main_keyboard(message.from_user.id))

    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Tugmasiz yuborish", callback_data="bc_no_btn")],
        [InlineKeyboardButton(text="➕ Tugma qo'shish (Link)", callback_data="bc_add_btn")]
    ])
    
    await state.set_state(AdminBroadcast.waiting_for_button)
    await message.answer("Xabarga havola (link) tugmasini qo'shishni xohlaysizmi?", reply_markup=kb)

@dp.callback_query(AdminBroadcast.waiting_for_button, lambda c: c.data == "bc_no_btn")
async def bc_send_now(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Yuborilmoqda...")
    data = await state.get_data()
    await start_broadcasting(callback.message, data['msg_id'], data['chat_id'], None)
    await state.clear()

@dp.callback_query(AdminBroadcast.waiting_for_button, lambda c: c.data == "bc_add_btn")
async def bc_ask_btn_data(callback: types.CallbackQuery):
    await callback.message.answer("Tugma matni va havolasini quyidagi formatda yuboring:\n\n<code>Tugma nomi | https://google.com</code>")
    await callback.answer()

@dp.message(AdminBroadcast.waiting_for_button)
async def bc_final_with_btn(message: types.Message, state: FSMContext):
    if "|" not in message.text:
        return await message.answer("Xato format! Namuna: <code>Batafsil | https://t.me/...</code>", parse_mode="HTML")
    
    parts = message.text.split("|")
    btn_text = parts[0].strip()
    btn_url = parts[1].strip()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=btn_url)]])
    
    data = await state.get_data()
    await start_broadcasting(message, data['msg_id'], data['chat_id'], kb)
    await state.clear()

async def start_broadcasting(msg_to_send, msg_id, chat_id, reply_markup):
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    
    count, blocked = 0, 0
    status_msg = await msg_to_send.answer(f"🚀 Tarqatish boshlandi... (0/{len(users)})")
    
    for user in users:
        try:
            await bot.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=chat_id,
                message_id=msg_id,
                reply_markup=reply_markup
            )
            count += 1
        except Exception:
            blocked += 1
        
        if count % 20 == 0:
            try: await status_msg.edit_text(f"⏳ Tarqatilmoqda... ({count}/{len(users)})")
            except Exception: pass
            await asyncio.sleep(0.5)

    await msg_to_send.answer(
        f"✅ <b>Xabar tarqatildi!</b>\n\n👤 Qabul qildi: {count}\n🚫 Bloklagan: {blocked}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(msg_to_send.chat.id)
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
