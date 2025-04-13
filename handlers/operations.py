from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.keybords import *
from utils.states import ProductStates
from utils.config import CONFIG
from repository.sheets import SheetManager

router = Router()

class ProductOperations:
    def __init__(self, sheet_manager):
        self.sheet_manager = sheet_manager

    def handle_reserve(self, category, product, attribute, amount):
        if not product.can_reserve_buy(amount):
            return self.get_not_enough_error(product)

        self.sheet_manager.reserve_product_amount(category, product, amount)
        return f"📌 Забронировано {amount} шт. товара {product.name} ({attribute})"

    def handle_release(self, category, product, attribute, amount):
        if not product.can_release(amount):
            return f"Недостаточно в брони. В резерве: {product.reserved}"

        self.sheet_manager.release_product_amount(category, product, amount)
        return f"🚫 Снято {amount} шт. товара {product.name} ({attribute})"

    def handle_buy(self, category, product, amount):
        total_available = product.available + product.reserved
        if total_available < amount:
            return self.get_not_enough_error(product, total_available)
        return self.sheet_manager.buy_product_amount(category, product, amount)

    def handle_add(self, category, product, attribute, amount):
        self.sheet_manager.add_product_amount(category, product, amount)
        return f"➕ Добавлено {amount} шт. товара {product.name} ({attribute})"

    @staticmethod
    def get_not_enough_error(product, amount=None):
        return f"Недостаточно товара. Доступно: {product.available if not amount else amount}"

@router.message(F.text.in_({"📌 Забронировать", "🚫 Снять бронь", "✅ Продать", "➕ Добавить количество"}))
async def start_product_operation(message: Message, state: FSMContext):
    await state.update_data(action=CONFIG.ACTIONS_MAP[message.text], order_items=[], context="operations")
    response = await message.answer("Доступные категории", reply_markup=get_category_keyboard())
    await state.update_data(inline_message_id=response.message_id)

@router.message(F.text == "🛍️ Новый заказ")
async def start_new_order(message: Message, state: FSMContext):
    await state.update_data(action="buy", order_items=[], is_order=True, context="operations")
    response = await message.answer("Выбери категорию товара", reply_markup=get_category_keyboard())
    await state.update_data(inline_message_id=response.message_id)

@router.callback_query(F.data == "cancel")
async def cancel_inline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Операция отменена")
    await callback.message.answer("Выберите следующее действие", reply_markup=get_operations_menu())
    await state.update_data(context="operations")
    await callback.answer()

@router.callback_query(F.data.startswith("category:"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, category = callback.data.split(":")
    data = await state.get_data()
    action = data.get("action")
    await state.update_data(category=category)

    product_names = sheet_manager.get_product_names(category, action)

    if not product_names:
        empty_keyboard = InlineKeyboardMarkup(inline_keyboard=[get_additional_row("back_to_categories")])
        await callback.message.edit_text(f"В этой категории нет подходящих товаров", reply_markup=empty_keyboard)
        await callback.answer()
        return

    await callback.message.edit_text(f"Товары в категории *\"{category}\"*",
                                     reply_markup=get_product_keyboard(product_names))
    await callback.answer()

@router.callback_query(F.data.startswith("product:"))
async def process_product_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, product_name = callback.data.split(":")
    data = await state.get_data()
    action, category = data.get("action"), data.get("category")
    await state.update_data(product_name=product_name)

    attributes = sheet_manager.get_product_attributes(category, product_name, action)

    await callback.message.edit_text(
        f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes))
    await callback.answer()

@router.callback_query(F.data.startswith("attribute:"))
async def process_attribute_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, attribute = callback.data.split(":")
    data = await state.get_data()
    action, category, product_name = data.get("action"), data.get("category"), data.get("product_name")

    await state.update_data(attribute=attribute)

    product = sheet_manager.find_product(category, product_name, attribute)
    qty = product.reserved if action == "release" else product.available + product.reserved if action == "buy" else product.available
    message_text = f"Выбери количество товара *\"{product_name} ({attribute})\"*\n"
    max_qty = qty if action != "add" else 5

    await callback.message.edit_text(message_text, reply_markup=get_quantity_keyboard(max_qty))
    await callback.answer()

@router.callback_query(F.data.startswith("quantity:"))
async def process_quantity_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    amount = int(callback.data.split(":")[1])
    data = await state.get_data()
    action, category, product_name, attribute = data.get("action"), data.get("category"), data.get(
        "product_name"), data.get("attribute")
    is_order, order_items = data.get("is_order", False), data.get("order_items", [])

    product = sheet_manager.find_product(category, product_name, attribute)
    await callback.message.edit_text(f"⏳ Выполняю операцию...")

    operations = ProductOperations(sheet_manager)

    if action == "buy":
        sale = operations.handle_buy(category, product, amount)

        if is_order:
            order_items.append(sale)
            await state.update_data(order_items=order_items)
            item_info = (f"🎉 Успешно добавлена продажа в заказ\n\n{sale.__str__()}\n"
                         f"Текущих товаров в заказе: {len(order_items)}\n"
                         f"Итоговая сумма: {sum(sale.total for sale in order_items)} грн")

            await callback.message.edit_text(item_info, reply_markup=get_order_continue_keyboard())
        else:
            await state.update_data(last_sale_id=sale.id)
            await callback.message.edit_text(f"🎉 Успешно оформлена продажа!\n\n{sale.__str__()}")
            await callback.message.answer("Выбери действие c продажей", reply_markup=get_order_action_keyboard())
    else:
        operation_handler = getattr(operations, f"handle_{action}")
        result_message = operation_handler(category, product, attribute, amount)
        await callback.message.edit_text(result_message)
        await callback.message.answer("Выбери действие", reply_markup=get_operations_menu())
        await state.clear()
        await state.update_data(context="operations")

    await callback.answer()

@router.callback_query(F.data.startswith("order_action:"))
async def process_order_action(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, action = callback.data.split(":")
    data = await state.get_data()
    sale_id = data.get("last_sale_id")
    sale = sheet_manager.get_sale_by_id(sale_id)

    if action == "create_order":
        await callback.message.edit_text("⏳ Создаю новый заказ...")
        order = sheet_manager.create_order([sale])
        order_summary = f"🎉 Успешно!\n\n{order.__str__()}\n\n🧬 Состав заказа:\n{sale.__str__()}\n"
        await callback.message.edit_text(order_summary)
        await callback.message.answer("Выбери действие", reply_markup=get_operations_menu())
        await state.clear()
        await state.update_data(context="operations")
    else:
        order_ids = sheet_manager.get_all_order_ids()
        if not order_ids:
            await callback.message.edit_text("Нет доступных заказов для добавления. Создай новый заказ",
                                             reply_markup=InlineKeyboardMarkup(
                                                 inline_keyboard=[[get_back_button("back_to_order_actions")
                                                                   ]]))
            await callback.answer()
            return

        ids_text = ", ".join(order_ids[:10])
        if len(order_ids) > 10:
            ids_text += f" и еще {len(order_ids) - 10}"

        await callback.message.edit_text(
            f"Введи ID заказа, к которому нужно добавить продажу\n\nДоступные ID заказов: {ids_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[get_back_button("back_to_order_actions")
                                                                ]]))
        await state.update_data(order_msg_id=callback.message.message_id, user_msgs=[])
        await state.set_state(ProductStates.ORDER_ID)

    await callback.answer()

@router.callback_query(F.data == "back_to_order_actions")
async def back_to_order_actions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    user_msgs = data.get("user_msgs", [])
    for msg_id in user_msgs:
        await callback.bot.delete_message(callback.message.chat.id, msg_id)

    await callback.message.edit_text("Выбери действие c продажей", reply_markup=get_order_action_keyboard())
    await state.set_state(None)
    await callback.answer()

@router.message(ProductStates.ORDER_ID)
async def process_order_id(message: Message, state: FSMContext, sheet_manager: SheetManager):
    order_id = message.text.strip()
    data = await state.get_data()
    sale_id = data.get("last_sale_id")
    sale = sheet_manager.get_sale_by_id(sale_id)

    user_msgs = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    await state.update_data(user_msgs=user_msgs)

    order = sheet_manager.add_to_order(order_id, sale)

    if not order:
        response = await message.answer("Заказ не найден. Попробуй еще раз")
        user_msgs.append(response.message_id)
        await state.update_data(user_msgs=user_msgs)
        return

    order_summary = f"🎉 Успешно!\n\n{order.__str__()}\n\n🧬 Состав заказа:\n"
    for i, item in enumerate(order.sales, 1):
        order_summary += f"{i} - {item.__str__()}\n"

    await message.answer(order_summary, reply_markup=get_operations_menu())
    await state.clear()
    await state.update_data(context="operations")

@router.callback_query(F.data.startswith("back_to_cat"))
async def back_to_categories(callback: CallbackQuery):
    await callback.message.edit_text("Доступные категории", reply_markup=get_category_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_prod"))
async def back_to_products(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    data = await state.get_data()
    action, category = data.get("action"), data.get("category")
    product_names = sheet_manager.get_product_names(category, action)
    await callback.message.edit_text(f"Товары в категории *\"{category}\"*",
                                     reply_markup=get_product_keyboard(product_names))
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_attr"))
async def back_to_attributes(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    data = await state.get_data()
    action, category, product_name = data.get("action"), data.get("category"), data.get("product_name")
    attributes = sheet_manager.get_product_attributes(category, product_name, action)
    await callback.message.edit_text(
        f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*",
        reply_markup=get_attribute_keyboard(attributes))
    await callback.answer()

@router.callback_query(F.data == "order_continue:add_more")
async def add_more_to_order(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию товара", reply_markup=get_category_keyboard())
    await callback.answer()

@router.callback_query(F.data == "order_continue:finish")
async def finish_order(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    data = await state.get_data()
    order_items = data.get("order_items", [])

    await callback.message.edit_text("⏳ Оформляем заказ...")

    order = sheet_manager.create_order(order_items)
    order_summary = f"🎉 Успешно!\n\n{order.__str__()}\n\n🧬 Состав заказа:\n"
    for i, item in enumerate(order_items, 1):
        order_summary += f"{i} - {item.__str__()}\n"

    await callback.message.edit_text(order_summary)
    await callback.message.answer("Выберите действие", reply_markup=get_operations_menu())
    await state.clear()
    await state.update_data(context="operations")
    await callback.answer()
