from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.keyboards import (
    get_orders_menu,
    get_products_menu,
    get_statistics_keyboard,
    get_order_actions_keyboard,
    get_order_continue_keyboard,
    get_order_items_keyboard,
    get_category_keyboard,
    get_product_keyboard,
    get_attribute_keyboard
)

from utils.config import CONFIG
from utils.shit_utils import format_order_msg
from utils.states import StatisticsStates
from service.order_service import OrderService
from service.product_service import ProductService

router = Router()

@router.callback_query(F.data.startswith("cancel:"))
async def handle_cancel(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Universal cancel handler"""
    destination = callback.data.split(":")[1]
    data = await state.get_data()
    context, order_id = data.get("context"), data.get("order_id")

    await state.clear()

    if destination.startswith("order-act") and order_id:
        order = order_service.get_order(order_id)
        order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
        response = await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
        await state.update_data(context="orders", order_id=order_id, action="view_edit", inline_message_id=response.message_id)
    else:
        await callback.message.edit_text("Операция отменена")
        if context in ["orders", "products"]:
            reply_markup = get_orders_menu() if context == "orders" else get_products_menu()
            await callback.message.answer("Выбери действие", reply_markup=reply_markup)
            await state.update_data(context=context)
        else:
            await callback.message.answer("Выбери период для статистики", reply_markup=get_statistics_keyboard())
            await state.set_state(StatisticsStates.SELECT_PERIOD)
            await state.update_data(context="statistics")

    await callback.answer()

@router.callback_query(F.data.startswith("back:"))
async def handle_back(callback: CallbackQuery, state: FSMContext, order_service: OrderService, product_service: ProductService):
    """Universal back handler"""
    destination = callback.data.split(":")[1]
    data = await state.get_data()
    order_id, action = data.get("order_id"), data.get("action")
    order = order_service.get_order(order_id)

    if destination == "order_actions":
        await callback.message.edit_text(f"Заказ {order.display_name}\n" + format_order_msg(order),
            reply_markup=get_order_actions_keyboard())

    elif destination == "order_continue":
        await callback.message.edit_text(f"Заказ {order.display_name}\n" + format_order_msg(order),
            reply_markup=get_order_continue_keyboard())

    elif destination == "order_items":
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери товар для изменения количества",
            reply_markup=get_order_items_keyboard(order.items, "edit_item"))

    cancel_to = "order-actions" if action in ["view_edit", "edit"] else ""

    if destination == "category":
        prefix = f"Заказ {order.display_name}\n\n" if order.name else "Новый заказ\n\n"
        await callback.message.edit_text(f"{prefix}Выбери категорию товара",
            reply_markup=get_category_keyboard(cancel_to))

    elif destination == "product":
        category, action = data.get("category"), data.get("action")
        product_names = product_service.get_product_names(category, action)
        await callback.message.edit_text(f"Товары в категории *\"{category}\"*",
             reply_markup=get_product_keyboard(product_names, cancel_to))
        await state.update_data(product_names=product_names)

    elif destination == "attribute":
        category, action, product_name = data.get("category"), data.get("action"), data.get("product_name")
        attributes = product_service.get_attributes(category, product_name, action)
        await callback.message.edit_text(f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
            reply_markup=get_attribute_keyboard(attributes, cancel_to))
        await state.update_data(attributes=attributes)

    await callback.answer()
