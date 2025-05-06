from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.keyboards import (
    get_orders_menu,
    get_order_actions_keyboard,
    get_order_items_keyboard,
    get_category_keyboard
)
from utils.config import format_order_msg
from service.order_service import OrderService

router = Router()

@router.callback_query(F.data.startswith("view_order:"))
async def view_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Show order details"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text)
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("complete_order:"))
async def complete_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Complete an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    success, message = order_service.complete_order(order)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
    else:
        await callback.message.edit_text(f"✅ Заказ {order.id} успешно завершен!\n\n"
            f"Сумма заказа: {order.total} грн\n\nЧистая прибыль: {order.profit} грн"
        )

    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("delete_order:"))
async def delete_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Delete an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    success, message = await order_service.delete_order(order)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
    else:
        await callback.message.edit_text(f"🗑️ Заказ {order.id} успешно удален!")

    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("edit_order:"))
async def edit_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Edit an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order) + "\n\nВыбери действие"
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await state.update_data(order_id=order.id)
    await callback.answer()

@router.callback_query(F.data.startswith("order_action:"))
async def handle_order_action(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle order edit actions"""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    if action == "add_item":
        await state.update_data(new_action="add_item")
        await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери категорию товара", reply_markup=get_category_keyboard())

    elif action == "remove_item":
        await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери товар для удаления",
            reply_markup=get_order_items_keyboard(order.items, "remove_item")
        )

    elif action == "edit_quantity":
        await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери товар для изменения количества",
            reply_markup=get_order_items_keyboard(order.items, "edit_item")
        )

    else:
        upd_order = order_service.get_order(order_id)
        await callback.message.edit_text(f"✅ Редактирование заказа {upd_order.id} завершено.\n\n")

        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
        await state.clear()
        await state.update_data(context="orders")

    await callback.answer()
