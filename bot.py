import asyncio, logging, os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from repository.sheets import SheetManager
from handlers import start, operations, sales, echo

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    await bot.delete_webhook(drop_pending_updates=True)

    storage = MemoryStorage()
    sheet_manager = SheetManager()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(SheetManagerMiddleware(sheet_manager))
    dp.callback_query.middleware(SheetManagerMiddleware(sheet_manager))

    dp.include_router(start.router)
    dp.include_router(operations.router)
    dp.include_router(sales.router)
    dp.include_router(echo.router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

class SheetManagerMiddleware:
    def __init__(self, sheet_manager):
        self.sheet_manager = sheet_manager

    async def __call__(self, handler, event, data):
        data["sheet_manager"] = self.sheet_manager
        return await handler(event, data)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
