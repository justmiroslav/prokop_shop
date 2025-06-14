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
    get_order_names_keyboard
)
from utils.shit_utils import format_order_msg
from utils.config import CONFIG
from utils.states import OrderStates
from service.order_service import OrderService

router = Router()

@router.callback_query(F.data.startswith("view_edit_order:"))
async def view_edit_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Show order details with edit options"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order) + "\nВыбери действие"
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await state.update_data(order_id=order.id, action="view_edit")
    await callback.answer()

@router.callback_query(F.data.startswith("complete_order:"))
async def select_completion_date(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Select completion date for an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    date_options = order_service.get_completion_date_options(order)
    await callback.message.edit_text(f"Выбери дату завершения заказа {order.display_name}",
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
        await callback.message.edit_text(f"{message}\n\n" + format_order_msg(order))

    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()

@router.callback_query(F.data.startswith("restore_date:"))
async def select_restore_date(callback: CallbackQuery, order_service: OrderService):
    """Handle restore date selection - show orders completed on that date"""
    date_str = callback.data.split(":")[1]
    selected_date = date.fromisoformat(date_str)

    order_data = order_service.get_completed_orders_display_names_by_date(selected_date)
    await callback.message.edit_text(f"Выбери заказ для активации",
        reply_markup=get_order_names_keyboard(order_data, "restore_order")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("restore_order:"))
async def restore_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Restore a completed order to pending state"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    active_order_names = order_service.get_active_order_names_list()
    if not order.name or order.name in active_order_names:
        await callback.message.edit_text(f"Заказ {order_id}\n\nДля восстановления необходимо задать уникальное имя")
        await state.set_state(OrderStates.ENTER_ORDER_NAME)
        await state.update_data(restore_order_id=order_id)
        await callback.answer()
        return

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

    message = order_service.delete_order(order)
    order_data = order_service.get_active_order_names()
    await state.clear()

    if not order_data:
        await callback.message.edit_text(message)
        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
        await state.update_data(context="orders")
    else:
        action, message_text, callback_prefix = CONFIG.ACTIONS_MAP["🗑️ Удалить заказ"]
        await callback.message.edit_text(message + "\n\n" + message_text,
            reply_markup=get_order_names_keyboard(order_data, callback_prefix)
        )
        await state.update_data(context="orders", action=action)
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

@router.callback_query(F.data.startswith("order_action:"))
async def handle_order_action(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle order edit actions"""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    if action == "back_to_list":
        order_data = order_service.get_active_order_names()
        action_data, message_text, callback_prefix = CONFIG.ACTIONS_MAP["📝 Активные заказы"]
        response = await callback.message.edit_text(message_text,
            reply_markup=get_order_names_keyboard(order_data, callback_prefix)
        )
        await state.clear()
        await state.update_data(context="orders", action=action_data, inline_message_id=response.message_id)
        await callback.answer()
        return

    if action == "add_item":
        await state.update_data(new_action="add_item")
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери категорию товара",
            reply_markup=get_category_keyboard(cancel_to="order-actions"))

    elif action == "edit_name":
        await state.update_data(new_action="edit_name")
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nВведи новое имя заказа")
        await state.set_state(OrderStates.ENTER_ORDER_NAME)

    elif action == "edit_profit":
        adjustments = order_service.get_profit_adjustments(order_id)

        if adjustments:
            await callback.message.edit_text(f"Заказ {order.display_name}\n\nСуществующие корректировки профита",
                reply_markup=get_all_adjustments_keyboard(adjustments))
        else:
            await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери тип корректировки профита",
                reply_markup=get_adjustment_keyboard())

    elif not order.items:
        suffix = "\nВыбери действие" if action in ["remove_item", "edit_quantity"] else "\nРедактирование не может быть завершено с заказом без товаров"
        await callback.message.edit_text(f"Заказ {order.display_name}\n" + format_order_msg(order) + suffix,
            reply_markup=get_order_actions_keyboard())
        await callback.answer()
        return

    elif action == "remove_item":
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери товар для удаления",
            reply_markup=get_order_items_keyboard(order.items, "remove_item"))

    elif action == "edit_quantity":
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери товар для изменения количества",
            reply_markup=get_order_items_keyboard(order.items, "edit_item"))

    await callback.answer()
