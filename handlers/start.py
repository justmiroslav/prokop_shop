from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from utils.keybords import get_main_menu, get_operations_menu
from auth_manager import auth_manager
from utils.states import AuthStates
from utils.config import CONFIG

router = Router()

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if auth_manager.is_user_banned(user_id):
        await message.answer("⛔️ Доступ запрещен. Вы заблокированы.")
        return

    if auth_manager.is_user_authorized(user_id):
        await state.update_data(context="main")
        await message.answer(
            f"Привет, *{message.from_user.first_name}*! Я бот для управления товарами *SkullShop*\n\nВыбери опцию",
            reply_markup=get_main_menu())
        return

    await state.set_state(AuthStates.WAITING_FOR_PASSWORD)
    await message.answer(
        f"Привет, *{message.from_user.full_name}*! Добро пожаловать в SkullShop\n\n"
        "Для доступа к функциям введи пароль"
    )

@router.message(AuthStates.WAITING_FOR_PASSWORD)
async def handle_password(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text != CONFIG.BOT_PASSWORD:
        remaining_attempts = auth_manager.add_failed_attempt(user_id)
        if remaining_attempts:
            await message.answer(f"❌ Неверный пароль\n\nОсталось попыток: {remaining_attempts}")
            return

        auth_manager.ban_user(user_id)
        await message.answer("⛔️ Превышено количество попыток\n\nДоступ заблокирован")
        await state.clear()
        return

    auth_manager.authorize_user(user_id)
    await state.clear()
    await state.update_data(context="main")
    await message.answer(
        f"Пароль принят, *{message.from_user.first_name}*! Теперь ты можешь пользоваться ботом\n\n"
        "Выбери опцию",
        reply_markup=get_main_menu()
    )

@router.message(F.text == "🔙 Назад")
async def back_to_prev_menu(message: Message, state: FSMContext):
    cur_state = await state.get_state()

    if cur_state:
        if cur_state.startswith("Sale"):
            context = "main"
            reply_kb = get_main_menu()
        else:
            context = "operations"
            reply_kb = get_operations_menu()
    else:
        context = "main"
        reply_kb = get_main_menu()

    await state.clear()
    await state.update_data(context=context)
    await message.answer("Выбери опцию", reply_markup=reply_kb)

@router.message(F.text == "🛒 Действия")
async def operations_menu(message: Message, state: FSMContext):
    await state.update_data(context="operations")
    await message.answer("Выбери опцию с товарами", reply_markup=get_operations_menu())
