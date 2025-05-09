from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple
from datetime import date

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
            [KeyboardButton(text="🛒 Заказы"), KeyboardButton(text="📦 Товары"), KeyboardButton(text="📊 Статистика")]
        ]
    )

def get_orders_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="➕ Новый заказ"), KeyboardButton(text="✅ Завершить заказ"), KeyboardButton(text="🗑️ Удалить заказ")],
            [KeyboardButton(text="📝 Редактировать заказ"), KeyboardButton(text="🔍 Активные заказы")],
            [KeyboardButton(text="💬 Сообщение клиенту"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_products_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="➕ Добавить количество"), KeyboardButton(text="➖ Убрать количество"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_active_orders_keyboard(order_ids: List[str], prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=order_id, callback_data=f"{prefix}:{order_id}")
        for order_id in order_ids
    ]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append([get_cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_statistics_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📅 Вчера"), KeyboardButton(text="📅 Эта неделя")],
            [KeyboardButton(text="📅 Этот месяц"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=category, callback_data=f"category:{category}")
        for category in CONFIG.PRODUCT_CATEGORIES.keys()
    ]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons + [get_cancel_button()]))

def get_product_keyboard(product_names: List[str]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=product_name, callback_data=f"product:{index}")
        for index, product_name in enumerate(product_names)
    ]
    keyboard = format_inline_kb(buttons)
    keyboard.append(get_additional_row("back_to_categories"))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_attribute_keyboard(attributes: List[str]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=attribute, callback_data=f"attribute:{index}")
        for index, attribute in enumerate(attributes)
    ]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append(get_additional_row("back_to_products"))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_quantity_keyboard(max_qty: int, callback_str: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"quantity:{i}")
        for i in range(1, min(max_qty + 1, 10))
    ]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append(get_additional_row(callback_str))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_order_continue_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ Добавить еще товар", callback_data="order_continue:add_more"),
        InlineKeyboardButton(text="✅ Завершить добавление", callback_data="order_continue:finish")
    ]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons))

def get_order_actions_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="order_action:add_item"),
        InlineKeyboardButton(text="➖ Удалить товар", callback_data="order_action:remove_item"),
        InlineKeyboardButton(text="📝 Изменить количество", callback_data="order_action:edit_quantity"),
        InlineKeyboardButton(text="💰 Изменить профит", callback_data="order_action:edit_profit"),
        InlineKeyboardButton(text="✅ Завершить редактирование", callback_data="order_action:finish")
    ]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons, 2))

def get_order_items_keyboard(order_items, action_prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for item in order_items:
        text = f"{item.product.full_name} - x{item.quantity}"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"{action_prefix}:{item.id}"))

    keyboard = format_inline_kb(buttons, 1)
    keyboard.append([get_back_button("back_to_order_actions")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_completion_date_keyboard(date_options: List[Tuple[date, str]]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=date_text, callback_data=f"completion_date:{d.isoformat()}")
        for d, date_text in date_options
    ]
    keyboard = format_inline_kb(buttons, 2)
    keyboard.append([get_cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_adjustment_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ Прибавить к профиту", callback_data="profit_adj:add"),
        InlineKeyboardButton(text="➖ Вычесть из профита", callback_data="profit_adj:subtract")
    ]
    keyboard = format_inline_kb(buttons, 1)
    keyboard.append(get_additional_row("back_to_order_actions"))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_all_adjustments_keyboard(adjustments) -> InlineKeyboardMarkup:
    buttons = []
    for adj in adjustments:
        prefix = "+" if adj.amount > 0 else ""
        text = f"{prefix} {adj.amount} грн: {adj.reason}"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"delete_adj:{adj.id}"))

    buttons.append(InlineKeyboardButton(text="➕ Добавить корректировку", callback_data="add_adj"))
    keyboard = format_inline_kb(buttons, 1)
    keyboard.append([get_back_button("back_to_order_actions")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
