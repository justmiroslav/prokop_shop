import asyncio, logging, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from database.session import init_db, Session
from repository.sheets import SheetManager
from middleware import DependencyMiddleware
from handlers import start, statistics, echo
from handlers.menu import actions, edit_order_callbacks, order_action_callbacks, select_product_callbacks, adj_order_callbacks
from handlers.navigation import navigation

async def main():
    init_db()

    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher(storage=MemoryStorage())

    session = Session()
    sheet_manager = SheetManager(session)

    dp.update.middleware(DependencyMiddleware(sheet_manager))

    await sheet_manager.start_background_tasks()

    dp.include_routers(
        start.router,
        actions.router,
        select_product_callbacks.router,
        order_action_callbacks.router,
        edit_order_callbacks.router,
        adj_order_callbacks.router,
        navigation.router,
        statistics.router,
        echo.router
    )

    try:
        logging.info("Bot starting...")
        await dp.start_polling(bot)
    finally:
        await sheet_manager.stop_background_tasks()
        session.close()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Critical error: {e}", exc_info=True)
