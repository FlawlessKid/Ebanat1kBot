from datetime import datetime, timezone, timedelta

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import database as db
import config

router = Router()


@router.message(CommandStart())
async def start_cmd(message: Message):
    user = await db.get_or_create_user(
        message.from_user.id, message.from_user.username or message.from_user.first_name
    )
    await message.answer(
        "👋 Привет! Это казино-бот для фана с друзьями.\n\n"
        f"Стартовый баланс: {user['balance']} монет.\n\n"
        "🎮 Команды:\n"
        "/balance — баланс\n"
        "/daily — ежедневная награда\n"
        "/slot <ставка> — слот-машина с джекпотом\n"
        "/dice <ставка> <число|чет|нечет> — кубик\n"
        "/coin <ставка> <орел|решка> — монетка\n"
        "/top — топ игроков\n\n"
        "Ещё бот запоминает ваши фразы и иногда выдаёт случайную в чат 😏"
    )


@router.message(Command("balance"))
async def balance_cmd(message: Message):
    user = await db.get_or_create_user(
        message.from_user.id, message.from_user.username or message.from_user.first_name
    )
    await message.answer(f"💰 Твой баланс: {user['balance']} монет.")


@router.message(Command("daily"))
async def daily_cmd(message: Message):
    user_id = message.from_user.id
    await db.get_or_create_user(user_id, message.from_user.username or message.from_user.first_name)
    last = await db.get_last_daily(user_id)
    now = datetime.now(timezone.utc)

    if last:
        last_dt = datetime.fromisoformat(last)
        elapsed = now - last_dt
        if elapsed < timedelta(hours=config.DAILY_COOLDOWN_HOURS):
            remaining = timedelta(hours=config.DAILY_COOLDOWN_HOURS) - elapsed
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes = rem // 60
            await message.reply(f"⏳ Уже забирал(а) награду. Приходи через {hours}ч {minutes}м.")
            return

    new_balance = await db.change_balance(user_id, config.DAILY_REWARD)
    await db.set_last_daily(user_id, now.isoformat())
    await message.answer(f"🎁 Ежедневная награда: +{config.DAILY_REWARD} монет!\nБаланс: {new_balance}")


@router.message(Command("top"))
async def top_cmd(message: Message):
    users = await db.top_users(10)
    if not users:
        await message.answer("Пока никто не играл.")
        return
    lines = ["🏆 Топ игроков:"]
    for i, u in enumerate(users, start=1):
        name = u["username"] or str(u["user_id"])
        lines.append(f"{i}. {name} — {u['balance']} монет")
    await message.answer("\n".join(lines))
