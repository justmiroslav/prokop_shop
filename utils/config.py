import os
from dotenv import load_dotenv
from dataclasses import dataclass, field

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD")
    SHEET_ID = os.getenv("SHEET_ID")
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENTIALS_FILE = "repository/credentials.json"
    SHEET_SALES = "Продажи"
    SHEET_ORDERS = "Заказы"

    EXCLUDED_SHEETS = ["Товарка", SHEET_SALES, SHEET_ORDERS]

    COL_PRODUCT = 0
    COL_ATTRIBUTE = 1
    COL_AVAILABLE = 2
    COL_RESERVED = 3
    COL_PRICE = 4

    PRODUCT_CATEGORIES: dict[str, str] = field(default_factory=dict)
    ACTIONS_MAP = {
        "📌 Забронировать": "reserve",
        "🚫 Снять бронь": "release",
        "✅ Продать": "buy",
        "➕ Добавить количество": "add"
    }

    MESSAGES_MAP = {
        "reserve": "бронирования",
        "release": "снятия брони",
        "buy": "продажи",
        "add": "добавления"
    }

    ATTRIBUTE_MAP = {
        "Смак": "вкус",
        "Cмак": "вкус",
        "Колір": "цвет",
        "Опір": "сопротивление"
    }

CONFIG = Config()
