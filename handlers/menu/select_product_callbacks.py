from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from utils.keyboards import (
    get_additional_row,
    get_category_keyboard,
    get_product_keyboard,
    get_attribute_keyboard,
    get_quantity_keyboard,
    get_products_menu,
    get_orders_menu,
    get_order_continue_keyboard,
    get_order_actions_keyboard
)
from utils.config import CONFIG, format_order_msg
from utils.states import OrderStates
from handlers.menu.navigation import back_to_attributes, cancel_operation
from service.order_service import OrderService
from service.product_service import ProductService

router = Router()

@router.callback_query(F.data.startswith("category:"))
async def select_category(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle category selection"""
    category = callback.data.split(":")[1]
    data = await state.get_data()
    action = data.get("action")

    product_names = product_service.get_product_names(category, action)
    if not product_names:
        empty_keyboard = InlineKeyboardMarkup(inline_keyboard=[get_additional_row("back_to_categories")])
        await callback.message.edit_text(f"В этой категории нет подходящих товаров", reply_markup=empty_keyboard)
        await callback.answer()
        return

    await callback.message.edit_text(f"Товары в категории *\"{category}\"*",
        reply_markup=get_product_keyboard(product_names)
    )

    await state.update_data(category=category, product_names=product_names)
    await callback.answer()

@router.callback_query(F.data.startswith("product:"))
async def select_product(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle product selection"""
    index = int(callback.data.split(":")[1])
    data = await state.get_data()
    category, action, product_names = data.get("category"), data.get("action"), data.get("product_names")

    product_name = product_names[index]
    attributes = product_service.get_attributes(category, product_name, action)
    await callback.message.edit_text(
        f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes)
    )

    await state.update_data(product_name=product_name, attributes=attributes)
    await callback.answer()

@router.callback_query(F.data.startswith("attribute:"))
async def select_attribute(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle attribute selection"""
    attribute_index = int(callback.data.split(":")[1])
    data = await state.get_data()
    category, action, product_name, attributes = data.get("category"), data.get("action"), data.get("product_name"), data.get("attributes")

    attribute = attributes[attribute_index]
    product = product_service.get_product(category, product_name, attribute)
    max_qty = 10 if action == "add" else min(product.quantity, 10)

    await callback.message.edit_text(
        f"Выбери количество товара *\"{product.full_name}*\"\n",
        reply_markup=get_quantity_keyboard(max_qty, "back_to_attributes")
    )

    await state.update_data(attribute=attribute)
    await state.set_state(OrderStates.SELECT_QUANTITY)
    await callback.answer()

@router.callback_query(OrderStates.SELECT_QUANTITY)
async def select_quantity(callback: CallbackQuery, state: FSMContext, order_service: OrderService, product_service: ProductService):
    """Handle quantity selection"""
    if callback.data == "back_to_attributes":
        return await back_to_attributes(callback, state, product_service)
    if callback.data == "cancel":
        return await cancel_operation(callback, state)

    quantity = int(callback.data.split(":")[1])
    data = await state.get_data()
    category, action, product_name, attribute, new_action = data.get("category"), data.get("action"), data.get("product_name"), data.get("attribute"), data.get("new_action")

    product = product_service.get_product(category, product_name, attribute)

    if action in ["add", "remove"]:
        if action == "add":
            success = await product_service.add_quantity(product, quantity)
            action_text = "добавлено"
        else:
            success = await product_service.remove_quantity(product, quantity)
            action_text = "убрано"

        if not success:
            await callback.message.edit_text(f"Ошибка при обновлении количества товара")
            await callback.message.answer("Выбери действие", reply_markup=get_products_menu())
            await state.clear()
            await state.update_data(context="products")
            await callback.answer()
            return

        await callback.message.edit_text(f"✅ Успешно {action_text} {quantity} шт. товара {product.full_name}\n\n"
            f"Новое количество: {product.quantity}"
        )
        await callback.message.answer("Выбери действие", reply_markup=get_products_menu())
        await state.clear()
        await state.update_data(context="products")
        await callback.answer()
        return

    order_id = data.get("order_id")
    order = order_service.get_order(order_id)
    success, item, message = await order_service.add_product_to_order(order, product, quantity)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
        await state.clear()
        await state.update_data(context="orders")
        await callback.answer()
        return

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_continue_keyboard())
    await state.clear()
    await state.update_data(context="orders", order_id=order.id, action=action)
    if new_action:
        await state.update_data(new_action=new_action)
    await callback.answer()

@router.callback_query(F.data.startswith("order_continue:"))
async def handle_order_continue(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle order continuation actions"""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    order_id, new_action = data.get("order_id"), data.get("new_action")
    order = order_service.get_order(order_id)

    if action == "add_more":
        await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери категорию товара", reply_markup=get_category_keyboard())
        await callback.answer()
        return

    if new_action == "add_item":
        order_text = f"Заказ {order.id}\n\n" + format_order_msg(order) + "\n\nВыбери действие"
        await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
        await callback.answer()
        return

    await callback.message.edit_text(f"✅ Заказ {order.id} успешно создан!\n\nСумма заказа: {order.total} грн")
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
    await callback.answer()
