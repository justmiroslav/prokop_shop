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
    message = "<b>🛒 Ваше замовлення:</b>\n\n"

    if not order.items:
        return "Замовлення пусте"

    for i, item in enumerate(order.items, 1):
        item_total = item.price * item.quantity
        message += f"- {item.product.full_name} x{item.quantity} = {format_price(item_total)} грн\n"

    discount = order.discount

    if discount < 0:
        message += f"\n<b>💰 До сплати:</b> <s>{format_price(order.total_items)}</s> {format_price(order.total)} грн"
        message += f"\n<b>🎁 Знижка:</b> {format_price(abs(discount))} грн"
    else:
        message += f"\n<b>💰 До сплати:</b> {format_price(order.total_items)} грн"

    return message

def format_order_msg(order: Order) -> str:
    """Format order message for Telegram"""
    if not order.items:
        return "Товары отсутствуют"

    order_text = "\nТовары:\n"
    for item in order.items:
        item_total = item.price * item.quantity
        order_text += f"- {item.product.full_name} x{item.quantity} - {format_price(item_total)} грн\n"

    if order.adjustments:
        order_text += f"\nСумма товаров: {format_price(order.total_items)} грн\n"

        order_text += "\nКорректировки:\n"
        for adj in order.adjustments:
            prefix = "+" if adj.amount > 0 else "-"
            order_text += f"{prefix} {format_price(abs(adj.amount))} грн: {adj.reason}\n"

    order_text += f"\nСумма: {format_price(order.total)} грн, Прибыль: {format_price(order.profit)} грн\n"

    return order_text

def format_date_for_display(date_value: date) -> str:
    """Format date for display in Telegram messages"""
    days_diff = (datetime.now().date() - date_value).days
    return "Сегодня" if days_diff == 0 else "Вчера" if days_diff == 1 else f"{date_value.day} {CONFIG.MONTHS[date_value.month]}"

def get_date_range(order: Order) -> List[Tuple[date, str]]:
    """Get available completion date options"""
    today = datetime.now().date()
    earliest_date = max(today - timedelta(days=3), order.created_at.date())

    dates = []
    for i in range((today - earliest_date).days + 1):
        current_date = today - timedelta(days=i)
        date_str = format_date_for_display(current_date)
        dates.append((current_date, date_str))

    return dates

def format_dates_with_orders(completed_dates: List[date]) -> List[Tuple[date, str]]:
    """Format list of dates that have completed orders"""
    return [(d, format_date_for_display(d)) for d in completed_dates]

def build_date_period(period: str) -> Tuple[datetime, datetime, str]:
    """Get start and end dates for a period"""
    now = datetime.now()

    if period == "today":
        start_date = datetime(now.year, now.month, now.day)
        end_date = now
        name = "сегодня"
    elif period == "yesterday":
        yesterday = now - timedelta(days=1)
        start_date = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_date = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        name = "вчера"
    elif period == "week":
        start_of_week = now - timedelta(days=now.weekday())
        start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
        end_date = now
        name = "эту неделю"
    elif period == "month":
        start_date = datetime(now.year, now.month, 1)
        end_date = now
        name = "этот месяц"
    else:
        raise ValueError("Invalid period")

    return start_date, end_date, name
