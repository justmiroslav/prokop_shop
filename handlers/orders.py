from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.models import Order
from repository.order_repository import OrderRepository
from utils.keyboards import *
from utils.config import CONFIG
from utils.states import OrderStates
from service.order_service import OrderService
from service.product_service import ProductService

router = Router()

def format_order_msg(order: Order) -> str:
    """Format order output"""
    order_text = "Товары:\n"

    for i, item in enumerate(order.items, 1):
        order_text += f"- {item.product.full_name} x{item.quantity} - {item.price * item.quantity} грн\n"

    return order_text + f"\nСума: {order.total} грн, Прибыль: {order.profit} грн"

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
        f"Открыт новый заказ {order.id}\n\nВыбери категорию товара",
        reply_markup=get_category_keyboard()
    )

    await state.update_data(order_id=order.id, context="orders", action="new_order", message_id=response.message_id, inline_message_id=response.message_id)

@router.message(F.text == "🔍 Активные заказы")
async def show_active_orders(message: Message, state: FSMContext, order_service: OrderService):
    """Show active orders"""
    active_order_ids = order_service.get_active_order_ids()

    if not active_order_ids:
        await message.answer("Нет активных заказов", reply_markup=get_orders_menu())
        return

    response = await message.answer(
        f"Активные заказы",
        reply_markup=get_active_orders_keyboard(active_order_ids, "view_order")
    )

    await state.update_data(context="orders", action="view", inline_message_id=response.message_id)

@router.message(F.text == "✅ Завершить заказ")
async def complete_order_menu(message: Message, state: FSMContext, order_service: OrderService):
    """Show menu to complete an order"""
    active_order_ids = order_service.get_active_order_ids()

    if not active_order_ids:
        await message.answer("Нет активных заказов", reply_markup=get_orders_menu())
        return

    response = await message.answer(
        "Выбери заказ для завершения",
        reply_markup=get_active_orders_keyboard(active_order_ids, "complete_order")
    )

    await state.update_data(context="orders", action="complete", inline_message_id=response.message_id)

@router.message(F.text == "🗑️ Удалить заказ")
async def delete_order_menu(message: Message, state: FSMContext, order_service: OrderService):
    """Show menu to delete an order"""
    active_order_ids = order_service.get_active_order_ids()

    if not active_order_ids:
        await message.answer("Нет активных заказов", reply_markup=get_orders_menu())
        return

    response = await message.answer(
        "Выбери заказ для удаления",
        reply_markup=get_active_orders_keyboard(active_order_ids, "delete_order")
    )

    await state.update_data(context="orders", action="delete", inline_message_id=response.message_id)

@router.message(F.text == "📝 Редактировать заказ")
async def edit_order_menu(message: Message, state: FSMContext, order_service: OrderService):
    """Show menu to edit an order"""
    active_order_ids = order_service.get_active_order_ids()

    if not active_order_ids:
        await message.answer("Нет активных заказов")
        return

    response = await message.answer(
        "Выбери заказ для редактирования",
        reply_markup=get_active_orders_keyboard(active_order_ids, "edit_order")
    )

    await state.update_data(context="orders", action="edit", inline_message_id=response.message_id)

@router.message(F.text.in_({"➕ Добавить количество", "➖ Убрать количество"}))
async def start_product_operation(message: Message, state: FSMContext, product_service: ProductService):
    """Start product operation (add or remove quantity)"""
    categories = product_service.get_categories()
    if not categories:
        await message.answer("Нет доступных категорий товаров", reply_markup=get_orders_menu())
        return

    action = "add" if message.text == "➕ Добавить количество" else "remove"
    await state.update_data(action=action, context="products")

    response = await message.answer(f"Выбери категорию товара",
        reply_markup=get_category_keyboard()
    )

    await state.update_data(message_id=response.message_id, inline_message_id=response.message_id)

@router.callback_query(F.data.startswith("category:"))
async def select_category(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle category selection"""
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
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

    await callback.answer()

@router.callback_query(F.data.startswith("product:"))
async def select_product(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle product selection"""
    product_name = callback.data.split(":")[1]
    data = await state.get_data()
    category = data.get("category")
    action = data.get("action")

    await state.update_data(product_name=product_name)

    attributes = product_service.get_attributes(category, product_name, action)
    await callback.message.edit_text(
        f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes)
    )

    await callback.answer()

@router.callback_query(F.data.startswith("attribute:"))
async def select_attribute(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Handle attribute selection"""
    attribute = callback.data.split(":")[1]
    data = await state.get_data()
    category, product_name, action = data.get("category"), data.get("product_name"), data.get("action")

    await state.update_data(attribute=attribute)

    product = product_service.get_product(category, product_name, attribute)
    max_qty = 10 if action == "add" else min(product.quantity, 10)

    await callback.message.edit_text(
        f"Выбери количество товара *\"{product.full_name}*\"\n",
        reply_markup=get_quantity_keyboard(max_qty, "back_to_attributes")
    )

    await callback.answer()

@router.callback_query(F.data.startswith("quantity:"))
async def select_quantity(callback: CallbackQuery, state: FSMContext, order_service: OrderService, product_service: ProductService):
    """Handle quantity selection"""
    quantity = int(callback.data.split(":")[1])
    data = await state.get_data()
    category, product_name, attribute, action = data.get("category"), data.get("product_name"), data.get("attribute"), data.get("action")

    product = product_service.get_product(category, product_name, attribute)

    if action in ["add", "remove"]:
        if action == "add":
            success = product_service.add_quantity(product, quantity)
            action_text = "добавлено"
        else:
            success = product_service.remove_quantity(product, quantity)
            action_text = "убрано"

        if not success:
            await callback.message.edit_text(f"Ошибка при обновлении количества товара",
                reply_markup=get_category_keyboard()
            )
            return

        await callback.message.edit_text(f"✅ Успешно {action_text} {quantity} шт. товара {product.full_name}\n\n"
            f"Новое количество: {product.quantity}"
        )
        await callback.message.answer("Выбери действие", reply_markup=get_products_menu())

        await state.clear()
        await callback.answer()
        return

    order_id = data.get("order_id")
    order = order_service.get_order(order_id)
    success, item, message = order_service.add_product_to_order(order, product, quantity)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}", reply_markup=get_category_keyboard())
        return

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_continue_keyboard())
    await state.clear()
    await state.update_data(order_id=order.id, context="orders", action=action)
    await callback.answer()

@router.callback_query(F.data.startswith("order_continue:"))
async def handle_order_continue(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle order continuation actions"""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)

    if action == "add_more":
        await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери категорию товара", reply_markup=get_category_keyboard())

    elif action == "finish":
        if order.items:
            await callback.message.edit_text(f"✅ Заказ {order.id} успешно создан!\n\n"
                f"Сумма заказа: {order.total} грн"
            )
        else:
            await callback.message.edit_text("Заказ пуст, добавьте товары")

        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())

    await callback.answer()

@router.callback_query(F.data.startswith("view_order:"))
async def view_order(callback: CallbackQuery, order_service: OrderService):
    """Show order details"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text)
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("complete_order:"))
async def complete_order(callback: CallbackQuery, order_service: OrderService):
    """Complete an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    success, message = order_service.complete_order(order)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
        return

    await callback.message.edit_text(f"✅ Заказ {order.id} успешно завершен!\n\n"
        f"Сумма заказа: {order.total} грн\n\nЧистая прибыль: {order.profit} грн"
    )
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("delete_order:"))
async def delete_order(callback: CallbackQuery, order_service: OrderService):
    """Delete an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    success, message = order_service.delete_order(order)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
        return

    await callback.message.edit_text(f"🗑️ Заказ {order.id} успешно удален!")
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_order:"))
async def edit_order(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Edit an order"""
    order_id = callback.data.split(":")[1]
    order = order_service.get_order(order_id)

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order) + "\n\nВыбери действие"
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await state.update_data(edit_order_id=order.id)
    await callback.answer()

@router.callback_query(F.data.startswith("order_action:"))
async def handle_order_action(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle order edit actions"""
    action = callback.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("edit_order_id")
    order = order_service.get_order(order_id)

    if action == "edit_quantity":
        await callback.message.edit_text(
            f"Заказ {order.id}\n\nВыбери товар для изменения количества",
            reply_markup=get_order_items_keyboard(order.items, "edit_item")
        )

    elif action == "remove_item":
        await callback.message.edit_text(
            f"Заказ {order.id}\n\nВыбери товар для удаления",
            reply_markup=get_order_items_keyboard(order.items, "remove_item")
        )

    elif action == "add_item":
        await state.update_data(action="edit_order")
        await callback.message.edit_text(f"Заказ {order.id}\n\nВыбери категорию товара", reply_markup=get_category_keyboard())

    elif action == "finish":
        upd_order = order_service.get_order(order_id)
        await callback.message.edit_text(f"Редактирование заказа {order.id} завершено.\n\n"
            + format_order_msg(upd_order)
        )

        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())

    await callback.answer()

@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_quantity(callback: CallbackQuery, state: FSMContext, order_repo: OrderRepository):
    """Edit item quantity"""
    item_id = int(callback.data.split(":")[1])
    item = order_repo.get_order_item(item_id)

    await callback.message.edit_text(f"Товар: {item.product.full_name}\n\n"
        f"Текущее количество: {item.quantity}\n",
        reply_markup=get_quantity_keyboard(min(item.quantity + item.product.quantity, 10), "back_to_order_items")
    )

    await state.update_data(edit_item_id=item.id)
    await state.set_state(OrderStates.EDIT_QUANTITY)
    await callback.answer()

@router.callback_query(OrderStates.EDIT_QUANTITY, F.data.startswith("quantity:"))
async def update_item_quantity(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Update item quantity"""
    new_quantity = int(callback.data.split(":")[1])
    data = await state.get_data()
    item_id, order_id = data.get("edit_item_id"), data.get("edit_order_id")

    item = order_service.get_order_item(item_id)
    success, message = order_service.update_order_item_quantity(item, new_quantity)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
        await state.clear()
        return

    order = order_service.get_order(order_id)
    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)

    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await state.clear()
    await state.update_data(edit_order_id=order.id)
    await callback.answer(message)

@router.callback_query(F.data.startswith("remove_item:"))
async def remove_item(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Remove item from order"""
    item_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    order_id = data.get("edit_order_id")

    item = order_service.get_order_item(item_id)
    success, message = order_service.remove_order_item(item)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}")
        return

    order = order_service.get_order(order_id)
    if not order or not order.items:
        await callback.message.edit_text(f"Товары из заказа {order_id} удалены")
        await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
        await state.clear()
        return

    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu())
    await callback.answer(message)

@router.callback_query(F.data == "back_to_order_actions")
async def back_to_order_actions(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Go back to order actions"""
    data = await state.get_data()
    order_id = data.get("edit_order_id")

    order = order_service.get_order(order_id)
    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_actions_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_order_items")
async def back_to_order_items(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Go back to order items"""
    data = await state.get_data()
    order_id = data.get("edit_order_id")

    order = order_service.get_order(order_id)
    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    await callback.message.edit_text(order_text, reply_markup=get_order_items_keyboard(order.items, "edit_item"))
    await callback.answer()

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Go back to categories selection"""
    data = await state.get_data()
    order_id = data.get("order_id")
    if order_id:
        order = order_service.get_order(order_id)
        order_text = f"Заказ {order_id}\n\n" + format_order_msg(order)
    else:
        order_text = "Выбери категорию товара"

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

    await callback.answer()

@router.callback_query(F.data == "back_to_attributes")
async def back_to_attributes(callback: CallbackQuery, state: FSMContext, product_service: ProductService):
    """Go back to attributes selection"""
    data = await state.get_data()
    category = data.get("category")
    product_name = data.get("product_name")
    action = data.get("action")

    attributes = product_service.get_attributes(category, product_name, action)
    await callback.message.edit_text(
        f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes)
    )

    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_operation(callback: CallbackQuery, state: FSMContext):
    """Cancel current operation"""
    data = await state.get_data()
    context = data.get("context")
    await state.clear()
    await callback.message.edit_text("Операция отменена")
    await callback.message.answer("Выбери действие", reply_markup=get_orders_menu() if context == "orders" else get_products_menu())
    await state.update_data(context=context)
    await callback.answer()
