from aiogram import Router
from aiogram.types import Message, BufferedInputFile
from io import StringIO

from utils.keyboards import get_statistics_keyboard
from utils.config import CONFIG
from utils.states import StatisticsStates
from service.order_service import OrderService

router = Router()

@router.message(StatisticsStates.SELECT_PERIOD)
async def show_statistics(message: Message, order_service: OrderService):
    """Show statistics for a period"""
    period = CONFIG.PERIOD_MAP.get(message.text)
    if not period:
        await message.answer("Неизвестный период", reply_markup=get_statistics_keyboard())
        return

    try:
        start_date, end_date, period_name = order_service.get_date_period(period)
    except ValueError:
        await message.answer("Ошибка при получении периода", reply_markup=get_statistics_keyboard())
        return

    loading_msg = await message.answer(f"🔍 Подготовка статистики за *{period_name}*...")
    stats = order_service.get_statistics(start_date, end_date)

    if not stats["orders"]:
        await loading_msg.delete()
        await message.answer(f"Заказы за *{period_name}* не найдены", reply_markup=get_statistics_keyboard())
        return

    stats_text = f"📊 *Статистика за {period_name}*\n\n"
    stats_text += f"Всего заказов: *{stats['count']}*\n\n"
    stats_text += f"Общая выручка: *{stats['gross_revenue']:.2f} грн*\n\n"
    stats_text += f"Чистая прибыль: *{stats['net_profit']:.2f} грн*"

    detailed_report = create_detailed_report(stats, period_name)

    await loading_msg.delete()
    await message.answer(stats_text, reply_markup=get_statistics_keyboard())

    await message.answer_document(
        BufferedInputFile(
            detailed_report.getvalue().encode("utf-8"),
            filename=f"stats_{period}_{start_date.strftime('%Y%m%d')}.txt"
        ),
        caption="Файл с подробной статистикой по всем заказам за период"
    )

def create_detailed_report(stats, period_name):
    """Create detailed statistics report"""
    detailed_report = StringIO()
    detailed_report.write(f"Статистика по заказам за {period_name}\n\n")

    for order in stats["orders"]:
        detailed_report.write(f"Заказ #{order.id}\n")
        detailed_report.write(f"Дата завершения: {order.completed_at.strftime('%d.%m.%Y %H:%M')}\n")
        detailed_report.write(f"Сумма: {order.total:.2f} грн\n\n")
        detailed_report.write(f"Прибыль: {order.profit:.2f} грн\n\n")

        detailed_report.write("Товары:\n")
        for item in order.items:
            detailed_report.write(f"- {item.product.full_name} x{item.quantity} шт.\n")

        detailed_report.write("\n")

    return detailed_report
