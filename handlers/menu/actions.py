from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.keyboards import get_orders_menu, get_category_keyboard, get_order_names_keyboard, get_date_keyboard
from utils.config import CONFIG
from service.order_service import OrderService
from service.product_service import ProductService

router = Router()

@router.message(F.text == "➕ Новый заказ")
async def new_order(message: Message, state: FSMContext, order_service: OrderService, product_service: ProductService):
    """Start new order creation"""
    categories = product_service.get_categories()
    if not categories:
        await message.answer("Создание нового заказа невозможно\n\nНет доступных категорий товаров",
            reply_markup=get_orders_menu())
        return

    order = order_service.create_order()
    response = await message.answer(
        f"Открыт новый заказ\n\nВыбери категорию товара",
        reply_markup=get_category_keyboard()
    )

    await state.update_data(order_id=order.id, action="new_order", inline_message_id=response.message_id)

@router.message(F.text.in_({"🔍 Активные заказы", "✅ Завершить заказ", "🗑️ Удалить заказ", "📝 Редактировать заказ", "💬 Сообщение клиенту"}))
async def handle_order_commands(message: Message, state: FSMContext, order_service: OrderService):
    """Handle order-related commands"""
    order_data = order_service.get_active_order_names()

    if not order_data:
        await message.answer("Нет активных заказов", reply_markup=get_orders_menu())
        return

    action, message_text, callback_prefix = CONFIG.ACTIONS_MAP[message.text]
    response = await message.answer(message_text,
        reply_markup=get_order_names_keyboard(order_data, callback_prefix)
    )

    await state.update_data(action=action, inline_message_id=response.message_id)

@router.message(F.text == "🔄 Восстановить заказ")
async def handle_restore_order(message: Message, state: FSMContext, order_service: OrderService):
    """Start order restoration process - show date selection"""
    dates_with_orders = order_service.get_dates_with_completed_orders()

    if not dates_with_orders:
        await message.answer("За последние 3 дня нет завершенных заказов", reply_markup=get_orders_menu())
        return

    response = await message.answer("Выбери дату, за которую нужно восстановить заказ",
        reply_markup=get_date_keyboard(dates_with_orders, "restore_date")
    )

    await state.update_data(inline_message_id=response.message_id)

@router.message(F.text.in_({"➕ Добавить количество", "➖ Убрать количество"}))
async def start_product_operation(message: Message, state: FSMContext, product_service: ProductService):
    """Start product operation (add or remove quantity)"""
    categories = product_service.get_categories()
    if not categories:
        await message.answer("Нет доступных категорий товаров", reply_markup=get_orders_menu())
        return

    action = "add" if message.text == "➕ Добавить количество" else "remove"
    response = await message.answer(f"Выбери категорию товара",
        reply_markup=get_category_keyboard()
    )

    await state.update_data(action=action, inline_message_id=response.message_id)
