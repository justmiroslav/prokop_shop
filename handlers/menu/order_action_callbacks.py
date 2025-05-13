from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, date

from utils.keyboards import (
    get_orders_menu,
    get_order_actions_keyboard,
    get_order_items_keyboard,
    get_category_keyboard,
    get_date_keyboard,
    get_adjustment_keyboard,
    get_all_adjustments_keyboard,
    get_order_ids_keyboard
)
from utils.shit_utils import format_order_msg, format_price
from service.order_service import OrderService

router = Router()

@router.callback_query(F.data.startswith("view_order:"))
async def view_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Show order details"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n" + format_order_msg(order)
    await callback.message.edit_text(order_text)
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("complete_order:"))
async def select_completion_date(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Select completion date for an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    date_options = order_service.get_completion_date_options(order)
    await callback.message.edit_text(
        f"Выбери дату завершения заказа {order.id}",
        reply_markup=get_date_keyboard(date_options, "completion_date")
    )

    await state.update_data(order_id=order_id)
    await callback.answer()

@router.callback_query(F.data.startswith("completion_date:"))
async def complete_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Complete an order with selected date"""
    date_str = callback.data.split(":")[1]
    completion_date = datetime.fromisoformat(date_str)

    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    success, message = order_service.complete_order(order, completion_date)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
    else:
        await callback.message.edit_text(f"{message}\n\nСумма заказа: {format_price(order.total)} грн\nПрибыль: {format_price(order.profit)} грн")

    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("restore_date:"))
async def select_restore_date(callback: CallbackQuery, order_service: OrderService):
    """Handle restore date selection - show orders completed on that date"""
    date_str = callback.data.split(":")[1]
    selected_date = date.fromisoformat(date_str)

    completed_order_ids = order_service.get_completed_order_ids_by_date(selected_date)
    await callback.message.edit_text(f"Выбери заказ для активации",
        reply_markup=get_order_ids_keyboard(completed_order_ids, "restore_order")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("restore_order:"))
async def restore_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Restore a completed order to pending state"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    message = order_service.restore_order(order)
    await callback.message.edit_text(message)

    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("delete_order:"))
async def delete_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Delete an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    message = await order_service.delete_order(order)
    await callback.message.edit_text(message)

    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("customer_msg_order:"))
async def generate_customer_message(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Generate customer message for order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    message_text = order_service.get_customer_message(order)
    await callback.message.edit_text(message_text, parse_mode="HTML")
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("edit_order:"))
async def edit_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Edit an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n" + format_order_msg(order) + "\nВыбери действие"
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
        if not order.items:
            await callback.message.edit_text(f"Заказ {order.id}\n" + format_order_msg(order) + "\nВыбери действие", reply_markup=get_order_actions_keyboard())
        else:
            await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери товар для удаления",
                reply_markup=get_order_items_keyboard(order.items, "remove_item")
            )

    elif action == "edit_quantity":
        if not order.items:
            await callback.message.edit_text(f"Заказ {order.id}\n" + format_order_msg(order) + "\nВыбери действие", reply_markup=get_order_actions_keyboard())
        else:
            await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери товар для изменения количества",
                reply_markup=get_order_items_keyboard(order.items, "edit_item")
            )

    elif action == "edit_profit":
        adjustments = order_service.get_profit_adjustments(order_id)

        if adjustments:
            await callback.message.edit_text(f"Заказ {order.id}\n\nСуществующие корректировки профита",
                reply_markup=get_all_adjustments_keyboard(adjustments)
            )
        else:
            await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери тип корректировки профита",
                reply_markup=get_adjustment_keyboard()
            )

    else:
        upd_order = order_service.get_order(order_id)
        if not upd_order.items:
            order_text = f"Заказ {order.id}\n" + format_order_msg(order) + "\nРедактирование не может быть завершено с заказом без товаров"
            await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
            await callback.answer()
            return

        await callback.message.edit_text(f"✅ Редактирование заказа {upd_order.id} завершено")
        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
        await state.clear()
        await state.update_data(context="orders")

    await callback.answer()
