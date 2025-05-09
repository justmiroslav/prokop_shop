from decimal import Decimal
from typing import Union, List, Tuple
from datetime import datetime, timedelta, date
import math

from database.models import Order
from utils.config import CONFIG

def format_price(value: Union[float, int, Decimal]) -> str:
    """Format price for Telegram message"""
    if isinstance(value, Decimal):
        value = float(value)

    if value == int(value):
        return str(int(value))

    decimal_part = abs(value) - abs(math.floor(value))
    if decimal_part < 0.01 or decimal_part >= 0.1:
        return f"{value:.2f}"
    return str(float(value))

def format_customer_message(order) -> str:
    """Format customer message for Telegram"""
    message = "🛒 *Ваше замовлення:*\n\n"

    for i, item in enumerate(order.items, 1):
        item_total = item.price * item.quantity
        message += f"- {item.product.full_name} x{item.quantity} = {format_price(item_total)} грн\n"

    message += f"\n💰 *До сплати:* {format_price(order.total)} грн"

    return message

def format_order_msg(order: Order) -> str:
    """Format order message for Telegram"""
    order_text = "Товары:\n"

    for i, item in enumerate(order.items, 1):
        item_total = item.price * item.quantity
        order_text += f"- {item.product.full_name} x{item.quantity} - {format_price(item_total)} грн\n"

    order_text += f"\nСума: {format_price(order.total)} грн"

    if order.adjustments:
        order_text += f", Расчетная прибыль: {format_price(order.ideal_profit)} грн\n"
        order_text += "\nКорректировки:\n"

        for adj in order.adjustments:
            prefix = "+" if adj.amount > 0 else ""
            order_text += f"\n{prefix} {format_price(adj.amount)} грн: {adj.reason}"

        order_text += f"\nИтоговая прибыль: {format_price(order.actual_profit)} грн"
    else:
        order_text += f", Прибыль: {format_price(order.ideal_profit)} грн"

    return order_text

def get_date_range(order: Order) -> List[Tuple[date, str]]:
    """Get available completion date options"""
    today = datetime.now().date()
    earliest_date = max(today - timedelta(days=3), order.created_at.date())

    dates = []
    for i in range((today - earliest_date).days + 1):
        current_date = today - timedelta(days=i)
        date_str = "Сегодня" if i == 0 else "Вчера" if i == 1 else f"{current_date.day} {CONFIG.MONTHS[current_date.month]}"
        dates.append((current_date, date_str))

    return dates
