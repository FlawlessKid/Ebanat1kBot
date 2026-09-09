import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from handlers import casino, economy, admin, quotes


async def main():
    logging.basicConfig(level=logging.INFO)
    await db.init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: сначала конкретные команды, "повторяшка" — последней
    # (она ловит вообще любой текст, который не команда).
    dp.include_router(admin.router)
    dp.include_router(economy.router)
    dp.include_router(casino.router)
    dp.include_router(quotes.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
