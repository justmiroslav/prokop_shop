from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.keyboards import (
    get_order_actions_keyboard,
    get_order_items_keyboard,
    get_category_keyboard,
    get_product_keyboard,
    get_attribute_keyboard,
    get_orders_menu,
    get_products_menu,
    get_statistics_keyboard,
    get_order_continue_keyboard
)
from utils.config import CONFIG
from utils.shit_utils import format_order_msg
from utils.states import StatisticsStates
from service.order_service import OrderService
from service.product_service import ProductService

router = Router()

@router.callback_query(F.data == "back_to_order_continue")
async def back_to_order_continue(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_continue_keyboard())
    await callback.answer()
    return

@router.callback_query(F.data == "back_to_order_actions")
async def back_to_order_actions(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Go back to order actions"""
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_order_items")
async def back_to_order_items(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Go back to order items"""
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери товар для изменения количества",
        reply_markup=get_order_items_keyboard(order.items, "edit_item"))
    await callback.answer()

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Go back to categories selection"""
    data = await state.get_data()
    order_id = data.get("order_id")
    prefix = f"Заказ {order_id}\n\n" if order_id else ""
    order_text = f"{prefix}Выбери категорию товара"

    await callback.message.edit_text(order_text, reply_markup=get_category_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_products")
async def back_to_products(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Go back to products selection"""
    data = await state.get_data()
    category, action = data.get("category"), data.get("action")

    product_names = product_service.get_product_names(category, action)
    await callback.message.edit_text(f"Товары в категории *\"{category}\"*",
        reply_markup=get_product_keyboard(product_names)
    )

    await state.update_data(product_names=product_names)
    await callback.answer()

@router.callback_query(F.data == "back_to_attributes")
async def back_to_attributes(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Go back to attributes selection"""
    data = await state.get_data()
    context, category, action, product_name, order_id = data.get("context"), data.get("category"), data.get("action"), data.get("product_name"), data.get("order_id")

    attributes = product_service.get_attributes(category, product_name, action)
    await callback.message.edit_text(
        f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes)
    )

    await state.clear()
    await state.update_data(context=context, category=category, action=action, product_name=product_name, attributes=attributes, order_id=order_id)
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_operation(callback: CallbackQuery, state: FSMContext, order_service: OrderService = None):
    """Cancel current operation"""
    data = await state.get_data()
    context, order_id, new_action, action = data.get("context"), data.get("order_id"), data.get("new_action"), data.get("action")

    await state.clear()

    if order_id and new_action:
        order = order_service.get_order(order_id)
        order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
        await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
        await state.update_data(context=context, order_id=order.id, action=action)
    else:
        await callback.message.edit_text("Операция отменена")
        if context in ["orders", "products"]:
            reply_markup = get_orders_menu() if context == "orders" else get_products_menu()
            await callback.message.answer("Выбери действие", reply_markup=reply_markup)
        else:
            await callback.message.answer("Выбери период для статистики", reply_markup=get_statistics_keyboard())
            await state.set_state(StatisticsStates.SELECT_PERIOD)

        await state.update_data(context=context)

    await callback.answer()
