from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from repository.order_repository import OrderRepository
from utils.keyboards import get_quantity_keyboard, get_order_items_keyboard, get_order_continue_keyboard, get_order_actions_keyboard
from utils.shit_utils import format_order_msg
from service.order_service import OrderService

router = Router()

@router.callback_query(F.data.startswith("remove_item:"))
@router.callback_query(F.data.startswith("remove_from_new:"))
async def remove_item(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    action, item_id = callback.data.split(":")
    data = await state.get_data()
    order_id = data.get("order_id")

    item = order_service.get_order_item(int(item_id))
    order_service.remove_order_item(item)

    order = order_service.get_order(order_id)
    if not order.items:
        keyboard = get_order_continue_keyboard() if action == "remove_from_new" else get_order_actions_keyboard()
        await callback.message.edit_text(f"Заказ {order.display_name}\n" + format_order_msg(order), reply_markup=keyboard)
        await callback.answer()
        return

    await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери товар для удаления",
        reply_markup=get_order_items_keyboard(order.items, action))
    await callback.answer()

@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_quantity(callback: CallbackQuery, state: FSMContext, order_repo: OrderRepository):
    item_id = int(callback.data.split(":")[1])
    item = order_repo.get_order_item(item_id)

    await callback.message.edit_text(f"Товар: {item.product.full_name}\n\nТекущее количество: {item.quantity}\n",
        reply_markup=get_quantity_keyboard(min(item.quantity + item.product.quantity, 10),
        callback_str="order_items", exclude_qty=item.quantity, cancel_to="order-actions")
    )

    await state.update_data(item_id=item.id)
    await callback.answer()

@router.callback_query(F.data.startswith("quantity_order_items:"))
async def update_item_quantity(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    new_quantity = int(callback.data.split(":")[1])
    data = await state.get_data()

    item_id, order_id = data.get("item_id"), data.get("order_id")
    await state.clear()
    await state.update_data(context="orders", order_id=order_id, action="edit")

    item = order_service.get_order_item(item_id)
    order_service.update_order_item_quantity(item, new_quantity)

    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await callback.answer()
