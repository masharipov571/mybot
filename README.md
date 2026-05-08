# TSUE Study Assistant Bot

Telegram quiz boti va dars jadvali platforma.

## Loyiha tuzilishi

```
mybot/
├── main.py              # Asosiy kirish nuqtasi (FastAPI + Bot)
├── bot.py               # Telegram bot handlerlari (Aiogram 3)
├── api.py               # REST API endpointlari (FastAPI)
├── database.py          # SQLite ulanish va sozlash
├── models.py            # SQLAlchemy modellari
├── schemas.py           # Pydantic sxemalari
├── timetable_engine.py  # TSUE jadval screenshot (Playwright)
├── scheduler.py         # Kundalik xabarnomalar
├── migrate.py           # Baza migratsiyasi
├── requirements.txt     # Python kutubxonalar
├── Procfile             # Railway ishga tushirish
├── Dockerfile           # Docker konfiguratsiya
└── static/
    ├── index.html       # WebApp HTML
    ├── style.css        # Premium CSS dizayn
    └── app.js           # WebApp JavaScript mantiqi
```

## Railway Variables

Railway panelida **Variables** bo'limiga quyidagilarni qo'shing:

| Kalit | Qiymat | Ta'rif |
|-------|--------|--------|
| `BOT_TOKEN` | `1234567890:AAa...` | BotFather dan olingan token |
| `WEBAPP_URL` | `https://your-app.railway.app` | Railway URL (https bilan) |
| `ADMIN_TELEGRAM_ID` | `7294699676` | Sizning Telegram ID (ixtiyoriy) |

## Bot funksiyalari

### Telegram bot
- `/start` — Botni ishga tushirish
- `📚 Quiz WebApp` — WebApp platformasini ochish
- `📅 Dars Jadvali` — Guruh nomini kiritib jadval olish
- `🔔 Obuna Bo'lish` — Kundalik jadval obunasi
- `❌ Obunani Bekor Qilish` — Obunani bekor qilish

### WebApp (quiz platformasi)
- **Quiz Yaratish** — JSON fayl yuklash va quiz yaratish
- **Quizga Kirish** — 6 xonali kod bilan testga qo'shilish
- **Natijalarim** — O'rtacha natija va tarix statistika
- **Admin Panel** — 1213 kodi bilan kirish, quizlarni boshqarish

## Admin Panel

Admin paneliga kirish uchun:
1. Dashboard da **Admin Panel** tugmasini bosing
2. `1213` maxfiy kodini kiriting

Admin ID larini `api.py` dagi `ALLOWED_ADMINS` to'plamiga qo'shishingiz mumkin.

## GitHub ga yuklash tartibi

Quyidagi barcha fayllarni GitHub ga yuklang:

1. `main.py`
2. `bot.py`
3. `api.py`
4. `database.py`
5. `models.py`
6. `schemas.py`
7. `timetable_engine.py`
8. `scheduler.py`
9. `migrate.py`
10. `requirements.txt`
11. `Procfile`
12. `Dockerfile`
13. `static/index.html`
14. `static/style.css`
15. `static/app.js`
