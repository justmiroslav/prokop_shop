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
        if not self.can_reserve_or_buy(product, amount):
            return self.get_not_enough_error(product)

        self.sheet_manager.reserve_product_amount(category, product, amount)
        return f"📌 Забронировано {amount} шт. товара {product.name} ({attribute})"

    def handle_release(self, category, product, attribute, amount):
        if not self.can_release(product, amount):
            return f"Недостаточно в брони. В резерве: {product.reserved}"

        self.sheet_manager.release_product_amount(category, product, amount)
        return f"🚫 Снято {amount} шт. товара {product.name} ({attribute})"

    def handle_buy(self, category, product, attribute, amount):
        if not self.can_reserve_or_buy(product, amount):
            return self.get_not_enough_error(product)

        self.sheet_manager.buy_product_amount(category, product, amount)
        return f"✅ Продано {amount} шт. товара {product.name} ({attribute}) на сумму {product.price * amount} грн."

    def handle_add(self, category, product, attribute, amount):
        self.sheet_manager.add_product_amount(category, product, amount)
        return f"➕ Добавлено {amount} шт. товара {product.name} ({attribute})"

    @staticmethod
    def can_reserve_or_buy(product, amount):
        return product.can_reserve_buy(amount)

    @staticmethod
    def can_release(product, amount):
        return product.can_release(amount)

    @staticmethod
    def get_not_enough_error(product):
        return f"Недостаточно товара. Доступно: {product.available}"

def get_message_text_qty(action: str, category: str, product_name: str, attribute: str, qty: int) -> tuple[str, int]:
    end_message = "Текущее количество" if action == "add" else "В резерве" if action == "release" else "Доступно"
    return f"Выбери количество для {CONFIG.MESSAGES_MAP[action]}\n\nТовар: {product_name}\n{CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]].title()}: {attribute}\n{end_message}: {qty}", qty if action != "add" else 5

@router.message(F.text.in_({"📌 Забронировать", "🚫 Снять бронь", "✅ Продать", "➕ Добавить количество"}))
async def start_product_operation(message: Message, state: FSMContext):
    await state.update_data(action=CONFIG.ACTIONS_MAP[message.text])
    await message.answer("Доступные категории", reply_markup=get_category_keyboard())
    await state.set_state(ProductStates.CATEGORY)

@router.callback_query(F.data == "cancel")
async def cancel_inline(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Операция отменена")
    await callback.message.answer("Выберите следующее действие", reply_markup=get_operations_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("category:"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, category = callback.data.split(":")
    action = (await state.get_data()).get("action")
    await state.update_data(category=category)

    product_names = sheet_manager.get_product_names(category, action)

    if not product_names:
        empty_keyboard = InlineKeyboardMarkup(inline_keyboard=[get_additional_row("back_to_categories")])
        await callback.message.edit_text(f"В этой категории нет подходящих товаров", reply_markup=empty_keyboard)
        await callback.answer()
        return

    await callback.message.edit_text(f"Товары в категории *\"{category}\"*", reply_markup=get_product_keyboard(product_names))
    await state.set_state(ProductStates.PRODUCT)
    await callback.answer()

@router.callback_query(F.data.startswith("product:"))
async def process_product_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, product_name = callback.data.split(":")
    data = await state.get_data()
    action, category = data.get("action"), data.get("category")
    await state.update_data(product_name=product_name)

    attributes = sheet_manager.get_product_attributes(category, product_name, action)

    await callback.message.edit_text(f"Выбери {CONFIG.ATTRIBUTE_MAP[CONFIG.PRODUCT_CATEGORIES[category]]} товара *\"{product_name}\"*", reply_markup=get_attribute_keyboard(attributes))
    await state.set_state(ProductStates.ATTRIBUTE)
    await callback.answer()

@router.callback_query(F.data.startswith("attribute:"))
async def process_attribute_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    _, attribute = callback.data.split(":")
    data = await state.get_data()
    action, category, product_name = data.get("action"), data.get("category"), data.get("product_name")

    await state.update_data(attribute=attribute)

    product = sheet_manager.find_product(category, product_name, attribute)
    qty = product.reserved if action == "release" else product.available
    message_text, max_qty = get_message_text_qty(action, category, product_name, attribute, qty)

    await callback.message.delete()
    await callback.message.answer(message_text, reply_markup=get_quantity_keyboard(max_qty))
    await state.set_state(ProductStates.QUANTITY)
    await callback.answer()

@router.callback_query(F.data.startswith("quantity:"))
async def process_quantity_selection(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    amount = int(callback.data.split(":")[1])
    data = await state.get_data()
    action, category, product_name, attribute = data.get("action"), data.get("category"), data.get("product_name"), data.get("attribute")

    product = sheet_manager.find_product(category, product_name, attribute)
    await callback.message.edit_text(f"⏳ Выполняю операцию...")

    operation_handler = getattr(ProductOperations(sheet_manager), f"handle_{action}")
    result_message = operation_handler(category, product, attribute, amount)
    await callback.message.edit_text(result_message)
    await callback.message.answer("Выбери действие", reply_markup=get_operations_menu())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_cat"))
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Доступные категории", reply_markup=get_category_keyboard())
    await state.set_state(ProductStates.CATEGORY)
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_prod"))
async def back_to_products(callback: CallbackQuery, state: FSMContext, sheet_manager: SheetManager):
    data = await state.get_data()
    action, category = data.get("action"), data.get("category")
    product_names = sheet_manager.get_product_names(category, action)
    await callback.message.edit_text(f"Товары в категории *\"{category}\"*", reply_markup=get_product_keyboard(product_names))
    await state.set_state(ProductStates.PRODUCT)
    await callback.answer()
