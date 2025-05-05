import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from dataclasses import dataclass, field

load_dotenv()

def get_db_url():
    user: str = str(os.getenv("DB_USER", "postgres"))
    password: str = str(os.getenv("DB_PASSWORD", ""))

    return f"postgresql://{user}:{quote_plus(password)}@localhost:5432/skull_shop"

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD")
    SHEET_ID = os.getenv("SHEET_ID")
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENTIALS_FILE = "repository/credentials.json"
    EXCLUDED_SHEET = "Товарка"

    COL_PRODUCT = 0
    COL_ATTRIBUTE = 1
    COL_QUANTITY = 2
    COL_PRICE = 3
    COL_COST = 4

    PRODUCT_CATEGORIES: dict[str, str] = field(default_factory=dict)

    ATTRIBUTE_MAP = {
        "Смак": "вкус",
        "Cмак": "вкус",
        "Колір": "цвет",
        "Опір": "сопротивление"
    }

CONFIG = Config()
