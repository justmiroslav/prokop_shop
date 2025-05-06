from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.keyboards import get_main_menu, get_orders_menu, get_products_menu, get_statistics_keyboard

router = Router()

@router.message()
async def echo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    context, inline_message_id = data.get("context"), data.get("inline_message_id")

    if inline_message_id:
        await message.bot.edit_message_text(chat_id=message.chat.id,
            message_id=inline_message_id, text="Операция отменена"
        )
        kb = get_orders_menu() if context == "orders" else get_products_menu()
        await message.answer("Выбери действие", reply_markup=kb)
        await state.clear()
        await state.update_data(context=context)
        return

    reply_markup = get_orders_menu() if context == "orders" else get_products_menu() if context == "products" \
        else get_statistics_keyboard() if context == "statistics" else get_main_menu()

    await message.answer("Я не понимаю эту команду", reply_markup=reply_markup)
