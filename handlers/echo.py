from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.keybords import get_main_menu, get_operations_menu, get_sales_menu, get_date_keyboard, get_categories_sales_keyboard
from utils.states import SaleStates

router = Router()

@router.message()
async def echo_handler(message: Message, state: FSMContext):
    cur_state = await state.get_state()
    last_context = (await state.get_data()).get("context")
    if cur_state:
        reply_kb = get_date_keyboard() if cur_state == SaleStates.SELECT_PERIOD else get_categories_sales_keyboard()
    else:
        reply_kb = get_main_menu() if last_context == "main" else get_operations_menu() if last_context == "operations" else get_sales_menu()
    await message.answer("Я не понимаю эту команду", reply_markup=reply_kb)
