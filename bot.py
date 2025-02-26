import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import gspread
from google.oauth2.service_account import Credentials
from aiogram.client.default import DefaultBotProperties
from datetime import datetime

# Логирование
logging.basicConfig(level=logging.INFO)

# Настройки бота
TOKEN = "8046231684:AAEaOenNRW-mEr4Iv1afeTZQPd0bXyGfEzM"
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))

# Dispatcher через Router
router = Router()
dp = Dispatcher()
dp.include_router(router)

# Подключение к Google Таблице
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("core-dominion-452015-q6-97c65376a194.json", scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1-7cHP4gpw9WrprxjHf2oJQEGvzd-r-Ia3_mximmIuTA"
sheet = client.open_by_key(SPREADSHEET_ID)

# Выбор листа
@router.message(Command("start"))
async def start(message: types.Message):
    sheets = sheet.worksheets()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s.title, callback_data=f"sheet|{s.title}")]
            for s in sheets
        ]
    )
    await message.answer("Выберите лист:", reply_markup=keyboard)

# Обработка выбора листа
@router.callback_query(F.data.startswith("sheet|"))
async def select_sheet(call: CallbackQuery):
    sheet_name = call.data.split("|")[1]
    products = get_products(sheet_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=p, callback_data=f"product|{sheet_name}|{p}")]
            for p in products
        ]
    )
    await call.message.edit_text(f"Лист: {sheet_name}\nВыберите товар:", reply_markup=keyboard)
    await call.answer()

# Получение списка товаров из листа
def get_products(sheet_name):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        return [row[0] for row in data[1:] if row and row[0]]
    except Exception as e:
        logging.error(f"Ошибка получения товаров: {e}")
        return []

# Обработка выбора товара
@router.callback_query(F.data.startswith("product|"))
async def select_product(call: CallbackQuery):
    _, sheet_name, product = call.data.split("|")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📌 Забронировать", callback_data=f"action|{sheet_name}|{product}|booking")],
            [InlineKeyboardButton(text="✅ Продать", callback_data=f"action|{sheet_name}|{product}|sell")],
            [InlineKeyboardButton(text="🚫 Снять бронь", callback_data=f"action|{sheet_name}|{product}|remove")]
        ]
    )
    await call.message.edit_text(f"Товар: {product}\nВыберите действие:", reply_markup=keyboard)
    await call.answer()

# Обработка действий с товаром
@router.callback_query(F.data.startswith("action|"))
async def handle_product_action(call: CallbackQuery):
    _, sheet_name, product, action = call.data.split("|")
    if action == "booking":
        add_booking(sheet_name, product)
        text = f"🔹 Бронь добавлена для *{product}*! ✅"
    elif action == "sell":
        sell_product(sheet_name, product)
        text = f"✅ Товар *{product}* продан!"
    elif action == "remove":
        remove_booking(sheet_name, product)
        text = f"🚫 Бронь снята для *{product}*!"
    await call.message.edit_text(text)
    await call.answer()

# Функции работы с Google Таблицей
def add_booking(sheet_name, product):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        for i, row in enumerate(data):
            if row[0] == product:
                worksheet.update_cell(i + 1, 2, f"{row[1]} (бронь 1)")
                break
    except Exception as e:
        logging.error(f"Ошибка добавления брони: {e}")

def sell_product(sheet_name, product):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        for i, row in enumerate(data):
            if row[0] == product:
                quantity = int(''.join(filter(str.isdigit, row[1]))) - 1
                if quantity < 0:
                    quantity = 0
                worksheet.update_cell(i + 1, 2, str(quantity))
                add_to_sales(sheet_name, product)
                break
    except Exception as e:
        logging.error(f"Ошибка продажи: {e}")

def remove_booking(sheet_name, product):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        for i, row in enumerate(data):
            if row[0] == product and "бронь" in row[1]:
                new_value = row[1].replace(" (бронь 1)", "")
                worksheet.update_cell(i + 1, 2, new_value)
                break
    except Exception as e:
        logging.error(f"Ошибка снятия брони: {e}")

# Добавление в лист "Продажі" с датой и временем
def add_to_sales(sheet_name, product):
    try:
        sales_sheet = sheet.worksheet("Продажи")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sales_sheet.append_row([timestamp, sheet_name, product, "1 продаж"])
    except Exception as e:
        logging.error(f"Ошибка добавления в продажи: {e}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
