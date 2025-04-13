from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.keybords import get_main_menu, get_operations_menu, get_statistics_keyboard
from utils.states import SaleStates

router = Router()

@router.message()
async def echo_handler(message: Message, state: FSMContext):
    cur_state = await state.get_state()
    data = await state.get_data()
    context = data.get("context", "main")
    inline_message_id = data.get("inline_message_id")

    if inline_message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=inline_message_id,
            text="Операция отменена"
        )
        await message.answer("Выберите действие", reply_markup=get_operations_menu())
        await state.clear()
        await state.update_data(context="operations")
        return

    if cur_state:
        if cur_state == SaleStates.SELECT_PERIOD:
            reply_kb = get_statistics_keyboard()
        elif cur_state.startswith("ProductStates"):
            reply_kb = get_operations_menu()
        else:
            reply_kb = get_main_menu()
    else:
        if context == "operations":
            reply_kb = get_operations_menu()
        elif context == "sales":
            reply_kb = get_statistics_keyboard()
        else:
            reply_kb = get_main_menu()

    await message.answer("Я не понимаю эту команду", reply_markup=reply_kb)
