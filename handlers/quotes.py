import random
import time

from aiogram import Router, F
from aiogram.types import Message

import database as db
import config

router = Router()

_last_reply_time: dict[int, float] = {}


@router.message(F.text & ~F.text.startswith("/"))
async def collect_and_maybe_reply(message: Message):
    text = message.text.strip()

    if config.QUOTE_MIN_LEN <= len(text) <= config.QUOTE_MAX_LEN:
        await db.add_phrase(
            message.chat.id,
            message.from_user.id,
            message.from_user.username or message.from_user.first_name,
            text,
        )

    enabled = await db.get_setting("quotes_enabled")
    if enabled != "1":
        return

    chance_raw = await db.get_setting("quote_chance")
    chance = float(chance_raw) if chance_raw else config.QUOTE_REPLY_CHANCE

    now = time.time()
    last = _last_reply_time.get(message.chat.id, 0)
    if now - last < config.QUOTE_COOLDOWN_SECONDS:
        return

    if random.random() < chance:
        phrase = await db.get_random_phrase(message.chat.id, exclude_text=text)
        if phrase:
            _last_reply_time[message.chat.id] = now
            await message.answer(f"💭 {phrase['text']}")
