from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.keyboards import get_main_menu, get_orders_menu, get_products_menu, get_statistics_keyboard

router = Router()

@router.message()
async def echo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    context = data.get("context", "main")
    inline_message_id = data.get("inline_message_id")

    if inline_message_id:
        await message.bot.edit_message_text(chat_id=message.chat.id,
            message_id=inline_message_id, text="Операция отменена"
        )
        await message.answer("Выбери действие", reply_markup=get_orders_menu())
        await state.clear()
        await state.update_data(context="orders")
        return

    if context == "orders":
        reply_markup = get_orders_menu()
    elif context == "products":
        reply_markup = get_products_menu()
    elif context == "statistics":
        reply_markup = get_statistics_keyboard()
    else:
        reply_markup = get_main_menu()

    await message.answer("Я не понимаю эту команду", reply_markup=reply_markup)


