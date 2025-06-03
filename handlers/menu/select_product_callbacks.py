from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext

from utils.keyboards import (
    get_navigation_row,
    get_category_keyboard,
    get_product_keyboard,
    get_attribute_keyboard,
    get_quantity_keyboard,
    get_products_menu,
    get_orders_menu,
    get_order_continue_keyboard,
    get_order_actions_keyboard,
    get_order_items_keyboard
)
from utils.config import CONFIG
from utils.shit_utils import format_order_msg
from utils.states import OrderStates
from service.order_service import OrderService
from service.product_service import ProductService

router = Router()

@router.callback_query(F.data.startswith("category_"))
async def select_category(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle category selection"""
    call, category = callback.data.split(":")

    data = await state.get_data()
    action = data.get("action")

    product_names = product_service.get_product_names(category, action)
    if not product_names:
        empty_keyboard = InlineKeyboardMarkup(inline_keyboard=[get_navigation_row("category", cancel_to=call.split("_")[1])])
        await callback.message.edit_text(f"В этой категории нет подходящих товаров", reply_markup=empty_keyboard)
        await callback.answer()
        return

    await callback.message.edit_text(f"Товары в категории *\"{category}\"*",
        reply_markup=get_product_keyboard(product_names, cancel_to=call.split("_")[1]))

    await state.update_data(category=category, product_names=product_names)
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def select_product(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle product selection"""
    call, index_str = callback.data.split(":")
    index = int(index_str)

    data = await state.get_data()
    category, action, product_names = data.get("category"), data.get("action"), data.get("product_names")

    product_name = product_names[index]
    attributes = product_service.get_attributes(category, product_name, action)
    await callback.message.edit_text(f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes, cancel_to=call.split("_")[1])
    )

    await state.update_data(product_name=product_name, attributes=attributes)
    await callback.answer()

@router.callback_query(F.data.startswith("attribute_"))
async def select_attribute(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle attribute selection"""
    call, index_str = callback.data.split(":")
    index = int(index_str)

    data = await state.get_data()
    category, action, product_name, attributes = data.get("category"), data.get("action"), data.get("product_name"), data.get("attributes")

    attribute = attributes[index]
    product = product_service.get_product(category, product_name, attribute)
    max_qty = 10 if action == "add" else min(product.quantity, 10)

    await callback.message.edit_text(f"Выбери количество товара *\"{product.full_name}*\"\n",
        reply_markup=get_quantity_keyboard(max_qty, "attribute", cancel_to=call.split("_")[1])
    )

    await state.update_data(attribute=attribute)
    await callback.answer()

@router.callback_query(F.data.startswith("quantity_attribute:"))
async def select_quantity(callback: CallbackQuery, state: FSMContext, order_service: OrderService, product_service: ProductService):
    """Handle quantity selection"""
    quantity = int(callback.data.split(":")[1])
    data = await state.get_data()
    category, action, product_name, attribute, new_action = data.get("category"), data.get("action"), data.get("product_name"), data.get("attribute"), data.get("new_action")

    product = product_service.get_product(category, product_name, attribute)

    if action in ["add", "remove"]:
        if action == "add":
            await product_service.add_quantity(product, quantity)
            action_text = "добавлено"
        else:
            await product_service.remove_quantity(product, quantity)
            action_text = "убрано"

        await callback.message.edit_text(f"✅ Успешно {action_text} {quantity} шт. товара {product.full_name}\n\n"
            f"Новое количество: {product.quantity}")
        await callback.message.answer("Выбери действие", reply_markup=get_products_menu())
        await state.clear()
        await state.update_data(context="products")
        await callback.answer()
        return

    order_id = data.get("order_id")
    order = order_service.get_order(order_id)
    await order_service.add_product_to_order(order, product, quantity)

    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
    keyboard = get_order_actions_keyboard() if new_action else get_order_continue_keyboard()
    if new_action:
        order_text += "\nВыбери действие"

    await callback.message.edit_text(order_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("order_continue:"))
async def handle_order_continue(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle order continuation actions"""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("order_id")

    if action == "add_more":
        await callback.message.edit_text(f"Заказ {order_id}\n\nВыбери категорию товара", reply_markup=get_category_keyboard())

    elif action == "remove_item":
        order = order_service.get_order(order_id)
        await callback.message.edit_text(f"Заказ {order_id}\n\nВыбери товар для удаления",
            reply_markup=get_order_items_keyboard(order.items, "remove_from_new"))

    else:
        await callback.message.edit_text(f"Завершение заказа {order_id}\n\nВведи уникальное имя для него")
        await state.set_state(OrderStates.ENTER_ORDER_NAME)

    await callback.answer()

@router.message(OrderStates.ENTER_ORDER_NAME)
async def enter_order_name(message: Message, state: FSMContext, order_service: OrderService):
    """Handle order name input"""
    order_name = message.text.strip()

    if len(order_name) > 30:
        await message.answer("Имя заказа слишком длинное (более 30 символов)\n\nВведи имя заказа заново")
        return

    all_order_names = order_service.get_all_order_names()
    if order_name in all_order_names:
        await message.answer("Заказ с таким именем уже существует\n\nПожалуйста, введи другое имя")
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    order_service.update_order_name(order, order_name)
    await message.answer(f"✅ Заказ {order_name} успешно завершен!", reply_markup=get_orders_menu())
    await state.clear()
    await state.update_data(context="orders")
