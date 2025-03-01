from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from utils.keybords import get_main_menu, get_operations_menu, get_sales_menu

router = Router()

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.update_data(last_context="main")
    await message.answer(f"Привет, *{message.from_user.first_name}*! Я бот для управления товарами *SkullShop*\n\nВыбери опцию", reply_markup=get_main_menu())

@router.message(F.text == "🔙 Назад")
async def back_to_prev_menu(message: Message, state: FSMContext):
    cur_state = await state.get_state()
    reply_kb = get_main_menu() if not cur_state else get_sales_menu() if cur_state.startswith("SaleStates") else get_operations_menu()
    await message.answer("Выбери опцию", reply_markup=reply_kb)
    await state.clear()

@router.message(F.text == "🛒 Действия")
async def operations_menu(message: Message, state: FSMContext):
    await state.update_data(last_context="operations")
    await message.answer("Выбери опцию с товарами", reply_markup=get_operations_menu())

@router.message(F.text == "📈 Продажи")
async def sales_menu(message: Message, state: FSMContext):
    await state.update_data(last_context="sales")
    await message.answer("Выбери опцию с продажами", reply_markup=get_sales_menu())
