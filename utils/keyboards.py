from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple, Optional
from datetime import date

from utils.config import CONFIG
from utils.shit_utils import format_price

def format_inline_kb(buttons: list[InlineKeyboardButton], max_in_row: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:min(i + max_in_row, len(buttons))] for i in range(0, len(buttons), max_in_row)]

def get_cancel_button(cancel_to) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel:{cancel_to}")

def get_back_button(back_to: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 Назад", callback_data=f"back:{back_to}")

def get_navigation_row(back_to: str, cancel_to: str = "") -> list[InlineKeyboardButton]:
    return [get_back_button(back_to), get_cancel_button(cancel_to)]

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
            [KeyboardButton(text="📝 Редактировать заказ"), KeyboardButton(text="🔄 Восстановить заказ"), KeyboardButton(text="🔍 Активные заказы")],
            [KeyboardButton(text="💬 Сообщение клиенту"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_products_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="➕ Добавить количество"), KeyboardButton(text="➖ Убрать количество"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_order_names_keyboard(order_data: List[Tuple[str, str]], prefix: str, cancel_to: str = "") -> InlineKeyboardMarkup:
    """Create keyboard with order display names"""
    buttons = [
        InlineKeyboardButton(text=display_name, callback_data=f"{prefix}:{order_id}")
        for order_id, display_name in order_data
    ]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append([get_cancel_button(cancel_to)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_date_keyboard(date_options: List[Tuple[date, str]], prefix: str, cancel_to: str = "") -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=date_text, callback_data=f"{prefix}:{d.isoformat()}")
        for d, date_text in date_options
    ]
    keyboard = format_inline_kb(buttons, 2)
    keyboard.append([get_cancel_button(cancel_to)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_statistics_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📅 Вчера"), KeyboardButton(text="📅 Эта неделя")],
            [KeyboardButton(text="📅 Этот месяц"), KeyboardButton(text="🔙 Назад")]
        ]
    )

def get_category_keyboard(cancel_to: str = "") -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=category, callback_data=f"category_{cancel_to}:{category}")
        for category in CONFIG.PRODUCT_CATEGORIES.keys()
    ]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons + [get_cancel_button(cancel_to)]))

def get_product_keyboard(product_names: List[str], cancel_to: str = "") -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=product_name, callback_data=f"product_{cancel_to}:{index}")
        for index, product_name in enumerate(product_names)
    ]
    keyboard = format_inline_kb(buttons)
    keyboard.append(get_navigation_row("category", cancel_to))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_attribute_keyboard(attributes: List[str], cancel_to: str = "") -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=attribute, callback_data=f"attribute_{cancel_to}:{index}")
        for index, attribute in enumerate(attributes)
    ]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append(get_navigation_row("product", cancel_to))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_quantity_keyboard(max_qty: int, callback_str: str, cancel_to: str = "", exclude_qty: Optional[int] = None) -> InlineKeyboardMarkup:
    quantities = [i for i in range(1, min(max_qty + 1, 11)) if i != exclude_qty]
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"quantity_{callback_str}:{i}")
        for i in quantities
    ]
    keyboard = format_inline_kb(buttons, 3)
    keyboard.append(get_navigation_row(callback_str, cancel_to))
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_order_continue_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ Добавить еще товар", callback_data="order_continue:add_more"),
        InlineKeyboardButton(text="➖ Убрать товар", callback_data="order_continue:remove_item"),
        InlineKeyboardButton(text="✅ Завершить добавление", callback_data="order_continue:finish")
    ]
    return InlineKeyboardMarkup(inline_keyboard=format_inline_kb(buttons, 2))

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
        prefix = "❌ " if action_prefix.startswith("remove") else ""
        text = f"{prefix}{item.product.full_name}"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"{action_prefix}:{item.id}"))

    keyboard = format_inline_kb(buttons, 1)
    navigation = "order_continue" if action_prefix == "remove_from_new" else "order_actions"
    keyboard.append([get_back_button(navigation)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_adjustment_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="➕ Прибавить к профиту", callback_data="profit_adj:add"),
        InlineKeyboardButton(text="➖ Вычесть из профита", callback_data="profit_adj:subtract")
    ]
    keyboard = format_inline_kb(buttons, 1)
    keyboard.append([get_back_button("order_actions")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_all_adjustments_keyboard(adjustments) -> InlineKeyboardMarkup:
    buttons = []
    for adj in adjustments:
        prefix = "+" if adj.amount > 0 else "-"
        text = f"❌ {prefix} {format_price(abs(adj.amount))} грн: {adj.reason}"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"delete_adj:{adj.id}"))

    buttons.append(InlineKeyboardButton(text="➕ Добавить корректировку", callback_data="add_adj"))
    keyboard = format_inline_kb(buttons, 1)
    keyboard.append([get_back_button("order_actions")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
