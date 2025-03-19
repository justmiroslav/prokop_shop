from datetime import datetime, timedelta
from io import StringIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext

from utils.keybords import get_date_keyboard, get_sales_menu, get_categories_sales_keyboard
from utils.states import SaleStates
from repository.sheets import SheetManager
from utils.config import CONFIG
from utils.models import Sale

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

@router.message(F.text == "📅 По дате")
async def sales_by_date(message: Message, state: FSMContext):
    await message.answer("Выбери период", reply_markup=get_date_keyboard())
    await state.set_state(SaleStates.SELECT_PERIOD)

@router.message(F.text == "📊 По категории")
async def sales_by_category(message: Message, state: FSMContext):
    await message.answer("Выбери категорию", reply_markup=get_categories_sales_keyboard())
    await state.set_state(SaleStates.CATEGORY)

@router.message(SaleStates.SELECT_PERIOD)
async def process_date_selection(message: Message, state: FSMContext, sheet_manager: SheetManager):
    text = message.text

    if text == "🔙 Назад":
        await return_to_sales_menu(message, state)
        return

    period_params = get_date_period_params(text)
    if not period_params:
        await message.answer("Неверный выбор. Пожалуйста, используйте кнопки.")
        return

    await find_and_show_sales(message, state, sheet_manager.get_sales,
        f"🔍 Ищем продажи за *{period_params["period_name"]}*...",
        f"Продажи за *{period_params["period_name"]}* не найдены",
        f"📊 Продажи за *{period_params["period_name"]}*",
        args=(period_params["start_date"], period_params["end_date"])
    )

@router.message(SaleStates.CATEGORY)
async def process_category_selection(message: Message, state: FSMContext, sheet_manager: SheetManager):
    category = message.text

    if category == "🔙 Назад":
        await return_to_sales_menu(message, state)
        return

    if category not in CONFIG.PRODUCT_CATEGORIES:
        await message.answer("Неверная категория. Пожалуйста, выберите из предложенных.")
        return

    await find_and_show_sales(message, state, sheet_manager.get_sales_by_category,
        f"🔍 Ищем продажи для категории *\"{category}\"*...",
        f"Продажи для категории *\"{category}\"* не найдены",
        f"📊 Продажи для категории *\"{category}\"*",
        args=(category,)
    )

async def find_and_show_sales(message, state, get_sales_func, loading_text, not_found_text, report_title, args=()):
    loading_msg = await message.answer(loading_text)
    sales = get_sales_func(*args)
    await loading_msg.delete()

    if not sales:
        await message.answer(not_found_text, reply_markup=get_sales_menu())
        await state.clear()
        return

    await send_sales_report(message, state, sales, report_title)

@router.callback_query(F.data == "get_detailed_report")
async def get_detailed_report(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report, sales, report_message_id = data.get("report"), data.get("last_sales"), data.get("report_message_id")
    for sale in sales[10:]:
        report += sale.__str__() + "\n\n"

    detailed_report = StringIO()
    detailed_report.write(report)

    await callback.message.answer_document(BufferedInputFile(detailed_report.getvalue().encode("utf-8"),
        filename=f"sales_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"), caption="📋 Детальный отчет по продажам")
    await callback.bot.edit_message_text(chat_id=callback.message.chat.id, message_id=report_message_id,
        text=callback.message.text, reply_markup=None)
    await state.clear()
    await callback.answer()

async def send_sales_report(message: Message, state: FSMContext, sales: list[Sale], title: str):
    report = f"{title}:\n\n"
    report += f"Всего продаж: *{len(sales)}*\n"
    report += f"Общая сумма: *{sum(sale.total for sale in sales)} грн*\n"
    report += "📊 *Сводка по товарам:*\n\n"
    for sale in sales[:10]:
        report += sale.__str__() + "\n\n"

    report_message = await message.answer(report, reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Получить детальный отчет", callback_data="get_detailed_report")]
            ]
        )
    )
    await state.update_data(report=report, last_sales=sales, report_message_id=report_message.message_id)
    await message.answer("Выбери действие", reply_markup=get_sales_menu())

async def return_to_sales_menu(message: Message, state: FSMContext):
    await message.answer("Выберите отчет", reply_markup=get_sales_menu())
    await state.clear()
