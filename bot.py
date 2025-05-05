import asyncio, logging, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from database.session import init_db, Session
from repository.sheets import SheetManager
from middleware import DependencyMiddleware
from handlers import start, orders, statistics, echo

async def main():
    init_db()

    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    await bot.delete_webhook(drop_pending_updates=True)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    session = Session()
    sheet_manager = SheetManager(session)
    await sheet_manager.start_periodic_refresh()
    dp.update.middleware(DependencyMiddleware(sheet_manager))

    dp.include_router(start.router)
    dp.include_router(orders.router)
    dp.include_router(statistics.router)
    dp.include_router(echo.router)

    try:
        logging.info("Starting bot")
        await dp.start_polling(bot)
    finally:
        await sheet_manager.stop_periodic_refresh()
        session.close()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
