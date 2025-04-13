from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

from utils.config import CONFIG

def format_inline_kb(buttons: list[InlineKeyboardButton], max_in_row: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:min(i + max_in_row, len(buttons))] for i in range(0, len(buttons), max_in_row)]

def get_cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")

def get_back_button(data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 Назад", callback_data=data)

def get_additional_row(data: str) -> list[InlineKeyboardButton]:
    return [get_back_button(data), get_cancel_button()]

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="🛒 Действия"), KeyboardButton(text="📊 Статистика по дате")],
        ])

def get_operations_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📌 Забронировать"), KeyboardButton(text="🚫 Снять бронь"), KeyboardButton(text="✅ Продать")],
            [KeyboardButton(text="➕ Добавить количество"), KeyboardButton(text="🛍️ Новый заказ"), KeyboardButton(text="🔙 Назад")]
        ])

def get_statistics_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📅 Вчера"), KeyboardButton(text="📅 Эта неделя")],
            [KeyboardButton(text="📅 Этот месяц"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=category, callback_data=f"category:{category}") for category in CONFIG.PRODUCT_CATEGORIES.keys()]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons + [get_cancel_button()]))

def get_product_keyboard(product_names: set[str]) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=product_name, callback_data=f"product:{product_name}") for product_name in product_names]
    keyboard = format_inline_kb(buttons)
    keyboard.append(get_additional_row("back_to_categories"))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_attribute_keyboard(attributes: list[str]) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=attribute, callback_data=f"attribute:{attribute}") for attribute in attributes]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append(get_additional_row("back_to_products"))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_quantity_keyboard(max_qty: int) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=str(i), callback_data=f"quantity:{i}") for i in range(1, max_qty + 1)]
    keyboard = format_inline_kb(buttons, max_qty)
    keyboard.append(get_additional_row("back_to_attributes"))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_order_action_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text="🛍️ Создать заказ", callback_data="order_action:create_order"),
        InlineKeyboardButton(text="➕ Добавить в заказ", callback_data="order_action:add_to_order")]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons))

def get_order_continue_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text="➕ Добавить еще товар", callback_data="order_continue:add_more"),
        InlineKeyboardButton(text="✅ Завершить заказ", callback_data="order_continue:finish")]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons))
