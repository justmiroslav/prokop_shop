from datetime import datetime, timedelta
from io import StringIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext

from utils.keybords import get_statistics_keyboard, get_main_menu
from utils.states import SaleStates
from repository.sheets import SheetManager
from utils.models import Order

router = Router()

def get_date_period_params(text):
    now = datetime.now()

    if text == "📅 Сегодня":
        return {
            "start_date": datetime(now.year, now.month, now.day, 0, 0, 0),
            "end_date": now,
            "period_name": "сегодня"
        }
    elif text == "📅 Вчера":
        yesterday = now - timedelta(days=1)
        return {
            "start_date": datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0),
            "end_date": datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59),
            "period_name": "вчера"
        }
    elif text == "📅 Эта неделя":
        start_of_week = now - timedelta(days=now.weekday())
        return {
            "start_date": datetime(start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0),
            "end_date": now,
            "period_name": "эту неделю"
        }
    elif text == "📅 Этот месяц":
        return {
            "start_date": datetime(now.year, now.month, 1, 0, 0, 0),
            "end_date": now,
            "period_name": "этот месяц"
        }
    return None

@router.message(F.text == "📊 Статистика по дате")
async def show_date_selection(message: Message, state: FSMContext):
    await state.update_data(context="sales")
    await message.answer("Выбери период", reply_markup=get_statistics_keyboard())
    await state.set_state(SaleStates.SELECT_PERIOD)

@router.message(SaleStates.SELECT_PERIOD)
async def process_date_selection(message: Message, state: FSMContext, sheet_manager: SheetManager):
    text = message.text

    if text == "🔙 Назад":
        await message.answer("Выберите действие", reply_markup=get_main_menu())
        await state.update_data(context="main")
        await state.clear()
        return

    period_params = get_date_period_params(text)
    if not period_params:
        await message.answer("Неверный выбор. Пожалуйста, используйте кнопки.", reply_markup=get_statistics_keyboard())
        return

    await find_and_show_orders(message, state, sheet_manager.get_orders_by_date,
                               f"🔍 Ищем заказы за *{period_params['period_name']}*...",
                               f"Заказы за *{period_params['period_name']}* не найдены",
                               f"📊 Заказы за *{period_params['period_name']}*",
                               args=(period_params["start_date"], period_params["end_date"])
                               )

async def find_and_show_orders(message, state, get_orders_func, loading_text, not_found_text, report_title, args=()):
    loading_msg = await message.answer(loading_text)
    orders = get_orders_func(*args)
    await loading_msg.delete()

    if not orders:
        await message.answer(not_found_text, reply_markup=get_statistics_keyboard())
        return

    await send_orders_report(message, state, orders, report_title)

async def send_orders_report(message: Message, state: FSMContext, orders: list[Order], title: str):
    total_sales = sum(order.total for order in orders)

    report = f"{title}:\n\n"
    report += f"Всего заказов: *{len(orders)}*\n"
    report += f"Общая сумма: *{total_sales} грн*\n\n"
    report += "📋 Заказы:\n\n"

    for i, order in enumerate(orders[:5], 1):
        report += f"*{i}.* {order.__str__()}\n\n"
        report += "🧬 Состав заказа:\n\n"
        for sale in order.sales:
            report += sale.__str__() + "\n"

    has_more = len(orders) > 5
    if has_more:
        report += f"... и еще {len(orders) - 5} заказов"

    report_message = await message.answer(report, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Получить детальный отчет", callback_data="get_detailed_report")]
        ] if has_more else []
    ))
    await state.update_data(report=report, last_orders=orders, report_message_id=report_message.message_id)
    await message.answer("Выбери период", reply_markup=get_statistics_keyboard())

@router.callback_query(F.data == "get_detailed_report")
async def get_detailed_report(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report, orders = data.get("report"), data.get("last_orders")

    if len(orders) > 5:
        report = report.replace(f"... и еще {len(orders) - 5} заказов", "")

    for i, order in enumerate(orders[5:], 6):
        report += f"*{i}.* {order.__str__()}\n\n"
        report += "🧬 Состав заказа:\n\n"
        for sale in order.sales:
            report += sale.__str__() + "\n"

    detailed_report = StringIO()
    detailed_report.write(report)

    await callback.message.answer_document(BufferedInputFile(detailed_report.getvalue().encode("utf-8"),
                                                             filename=f"orders_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
                                           caption="📋 Детальный отчет по заказам")

    if report_message_id := data.get("report_message_id"):
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=report_message_id,
            reply_markup=None
        )

    await callback.answer()
