import sqlite3
import os


def migrate():
    """
    Mavjud bazaga yetishmayotgan ustunlarni qo'shadi.
    Bu Railway'da eski bazalar bilan ishlaganda kerak bo'ladi.
    """
    db_path = "/data/quiz_bot.db" if os.path.exists("/data") else "./quiz_bot.db"

    if not os.path.exists(db_path):
        print(f"[Migrate] Baza topilmadi: {db_path} — Skip")
        return

    print(f"[Migrate] Checking migrations in: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Mavjud ustunlarni tekshirish yordamchi funksiyasi
    def column_exists(table, column):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cursor.fetchall()]
        return column in cols

    # users jadvaliga is_admin qo'shish
    if not column_exists("users", "is_admin"):
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        print("[+] Added is_admin to users table")

    # results jadvaliga chunk_range qo'shish
    if not column_exists("results", "chunk_range"):
        cursor.execute("ALTER TABLE results ADD COLUMN chunk_range TEXT")
        print("[+] Added chunk_range to results table")

    # results jadvaliga date qo'shish
    if not column_exists("results", "date"):
        cursor.execute("ALTER TABLE results ADD COLUMN date DATETIME")
        print("[+] Added date to results table")

    # subscriptions jadvalini yaratish (agar mavjud bo'lmasa)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            group_name TEXT,
            notification_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("[+] Ensured subscriptions table exists")

    conn.commit()
    conn.close()
    print("[Migrate] Migration complete ✓")


if __name__ == "__main__":
    migrate()
