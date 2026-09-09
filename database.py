import random
from datetime import datetime, timezone

import aiosqlite

from config import DB_PATH, START_BALANCE, JACKPOT_SEED


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT {START_BALANCE},
                last_daily TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

        defaults = {
            "jackpot": str(JACKPOT_SEED),
            "quotes_enabled": "1",
            "quote_chance": "0.03",
        }
        for k, v in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        await db.commit()


async def get_or_create_user(user_id: int, username: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, balance, last_daily) VALUES (?, ?, ?, NULL)",
                (user_id, username, START_BALANCE),
            )
            await db.commit()
            return {"user_id": user_id, "username": username, "balance": START_BALANCE, "last_daily": None}
        if username:
            await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            await db.commit()
        return dict(row)


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def change_balance(user_id: int, delta: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_last_daily(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row and row[0] else None


async def set_last_daily(user_id: int, iso_time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (iso_time, user_id))
        await db.commit()


async def get_setting(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_jackpot() -> int:
    val = await get_setting("jackpot")
    return int(val) if val else 0


async def set_jackpot(value: int):
    await set_setting("jackpot", str(max(int(value), 0)))


async def add_phrase(chat_id: int, user_id: int, username: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO phrases (chat_id, user_id, username, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, username, text, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()


async def get_random_phrase(chat_id: int, exclude_text: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM phrases WHERE chat_id = ?", (chat_id,))
        rows = await cur.fetchall()
        if not rows:
            return None
        candidates = [r for r in rows if r["text"] != exclude_text] or list(rows)
        return dict(random.choice(candidates))


async def stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(balance),0) FROM users")
        users_count, total_balance = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM phrases")
        phrases_count = (await cur.fetchone())[0]
        return {
            "users_count": users_count,
            "total_balance": total_balance,
            "phrases_count": phrases_count,
        }


async def top_users(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def clear_phrases(chat_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if chat_id is None:
            await db.execute("DELETE FROM phrases")
        else:
            await db.execute("DELETE FROM phrases WHERE chat_id = ?", (chat_id,))
        await db.commit()
