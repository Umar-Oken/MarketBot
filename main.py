"""
Finite State Machine (FSM), Routers
"""

import asyncio
import logging
import os
import sys
from db import database
from aiogram import Bot, Dispatcher
from aiogram.utils.i18n import I18n, FSMI18nMiddleware
from dotenv import load_dotenv
from sqlalchemy import text

from bot.commands import delete_default_commands, set_default_commands
from bot.handlers import routers
from bot.middlewares import JoinChannelGroupMiddleware
from db.seed import seed

load_dotenv(".env")
dp = Dispatcher()
TOKEN = os.getenv('BOT_TOKEN')


def _ensure_user_created_at_column():
    """Add created_at column to users table if it doesn't exist."""
    try:
        database.execute(text("""
            ALTER TABLE users ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
        """))
        database.commit()
    except Exception:
        database.rollback()


async def on_startup(bot: Bot):
    database.create_all()
    _ensure_user_created_at_column()
    seed()
    await set_default_commands(bot)


async def on_shutdown(bot: Bot):
    await delete_default_commands(bot)


async def main() -> None:
    bot = Bot(token=TOKEN)  # noqa
    i18 = I18n(path='locales', default_locale='uz', domain="messages")
    dp.update.outer_middleware.register(FSMI18nMiddleware(i18))
    dp.update.outer_middleware.register(JoinChannelGroupMiddleware())
    dp.include_routers(*routers)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

