from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from repository.order_repository import OrderRepository
from utils.keyboards import get_quantity_keyboard, get_order_actions_keyboard
from utils.config import format_order_msg
from utils.states import OrderStates
from service.order_service import OrderService

router = Router()

@router.callback_query(F.data.startswith("remove_item:"))
async def remove_item(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Remove item from order"""
    item_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    order_id = data.get("order_id")

    item = order_service.get_order_item(item_id)
    success, message = await order_service.remove_order_item(item)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}", reply_markup=get_order_actions_keyboard())
        await callback.answer()
        return

    order = order_service.get_order(order_id)
    if not order or not order.items:
        await callback.message.edit_text(f"Товары из заказа {order_id} удалены", reply_markup=get_order_actions_keyboard())
        await callback.answer()
        return

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await callback.answer(message)

@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_quantity(callback: CallbackQuery, state: FSMContext, order_repo: OrderRepository):
    """Edit item quantity"""
    item_id = int(callback.data.split(":")[1])
    item = order_repo.get_order_item(item_id)

    await callback.message.edit_text(f"Товар: {item.product.full_name}\n\n"
        f"Текущее количество: {item.quantity}\n",
        reply_markup=get_quantity_keyboard(min(item.quantity + item.product.quantity, 10), "back_to_order_items")
    )

    await state.update_data(item_id=item.id, category=item.product.sheet_name, product_name=item.product.name, attribute=item.product.attribute)
    await state.set_state(OrderStates.EDIT_QUANTITY)
    await callback.answer()

@router.callback_query(OrderStates.EDIT_QUANTITY)
async def update_item_quantity(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Update item quantity"""
    new_quantity = int(callback.data.split(":")[1])
    data = await state.get_data()
    item_id, order_id = data.get("item_id"), data.get("order_id")
    await state.clear()
    await state.update_data(context="orders", order_id=order_id, action="edit")

    item = order_service.get_order_item(item_id)
    success, message = await order_service.update_order_item_quantity(item, new_quantity)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}", reply_markup=get_order_actions_keyboard())
        await callback.answer()
        return

    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await callback.answer()
