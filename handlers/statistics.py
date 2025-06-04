from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from io import StringIO

from utils.keyboards import get_statistics_keyboard, get_months_keyboard
from utils.config import CONFIG
from utils.shit_utils import format_price
from utils.states import StatisticsStates
from service.order_service import OrderService

router = Router()

@router.message(StatisticsStates.SELECT_PERIOD)
async def handle_period_selection(message: Message, order_service: OrderService):
    """Handle period selection"""
    period = CONFIG.PERIOD_MAP.get(message.text)

    if period == "month":
        months_data = order_service.get_available_months()
        await message.answer("Выберите месяц", reply_markup=get_months_keyboard(months_data))
        return

    if not period:
        await message.answer("Неизвестный период", reply_markup=get_statistics_keyboard())
        return

    await show_period_statistics(message, order_service, period)

@router.callback_query(F.data.startswith("month:"))
async def handle_month_selection(callback: CallbackQuery, order_service: OrderService):
    """Handle month selection"""
    _, year_str, month_str = callback.data.split(":")
    year, month = int(year_str), int(month_str)

    start_date, end_date, period_name = order_service.get_month_period(year, month)
    stats = order_service.get_statistics(start_date, end_date)

    if not stats["orders"]:
        await callback.message.edit_text(f"Заказы за {period_name} не найдены")
        return

    await callback.message.edit_text(format_statistics_text(stats, period_name))

    detailed_report = create_detailed_report(stats, period_name)
    await callback.message.answer_document(
        BufferedInputFile(detailed_report.getvalue().encode("utf-8"),
        filename=f"stats_{year}_{month:02d}.txt"),
        caption="Файл с подробной статистикой по всем заказам за период",
        reply_markup=get_statistics_keyboard()
    )
    await callback.answer()

async def show_period_statistics(message: Message, order_service: OrderService, period: str):
    """Show statistics for a standard period"""
    try:
        start_date, end_date, period_name = order_service.get_date_period(period)
    except ValueError:
        await message.answer("Ошибка при получении периода", reply_markup=get_statistics_keyboard())
        return

    stats = order_service.get_statistics(start_date, end_date)

    if not stats["orders"]:
        await message.answer(f"Заказы за {period_name} не найдены", reply_markup=get_statistics_keyboard())
        return

    stats_text = format_statistics_text(stats, period_name)
    detailed_report = create_detailed_report(stats, period_name)

    await message.answer(stats_text, reply_markup=get_statistics_keyboard())
    await message.answer_document(
        BufferedInputFile(detailed_report.getvalue().encode("utf-8"),
        filename=f"stats_{period}_{start_date.strftime('%Y%m%d')}.txt"),
        caption="Файл с подробной статистикой по всем заказам за период",
        reply_markup=get_statistics_keyboard()
    )

def format_statistics_text(stats: dict, period_name: str) -> str:
    """Format statistics text"""
    stats_text = f"📊 *Статистика за {period_name}*\n\n"
    stats_text += f"Всего заказов: *{stats['count']}*\n"
    stats_text += f"Общая сумма заказов: *{format_price(stats['total_sum'])} грн*\n"
    stats_text += f"Себестоимость заказов: *{format_price(stats['total_cost'])} грн*\n"

    if stats["total_adjustments"] != 0:
        stats_text += f"Сумма корректировок: *{format_price(stats['total_adjustments'])} грн*\n"

    stats_text += f"Прибыль: *{format_price(stats['net_profit'])} грн*"
    return stats_text

def create_detailed_report(stats: dict, period_name: str) -> StringIO:
    """Create detailed statistics report"""
    detailed_report = StringIO()
    detailed_report.write(f"Статистика по заказам за {period_name}\n\n")

    for order in stats["orders"]:
        detailed_report.write(f"----Заказ {order.display_name}----\n")
        detailed_report.write(f"Дата завершения: {order.completed_at.strftime('%d.%m.%Y')}\n")

        detailed_report.write("\nТовары:\n")
        for item in order.items:
            detailed_report.write(f"- {item.product.full_name} x{item.quantity}\n")

        if order.adjustments:
            detailed_report.write(f"\nСумма товаров: {format_price(order.total_items)} грн\n")

            detailed_report.write("\nКорректировки:\n")
            for adj in order.adjustments:
                prefix = "+" if adj.amount > 0 else "-"
                detailed_report.write(f"{prefix} {format_price(abs(adj.amount))} грн: {adj.reason}\n")

        detailed_report.write(f"\nСумма: {format_price(order.total)} грн\n")
        detailed_report.write(f"Прибыль: {format_price(order.profit)} грн\n")

        detailed_report.write("\n")

    return detailed_report
