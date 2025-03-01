from dataclasses import dataclass
from datetime import datetime

from utils.config import CONFIG

@dataclass
class Product:
    row: int
    name: str
    attribute: str
    available: int
    reserved: int
    price: float

    def can_reserve_buy(self, amount: int) -> bool:
        return self.available >= amount

    def can_release(self, amount: int) -> bool:
        return self.reserved >= amount

    def reserve(self, amount: int) -> None:
        self.reserved += amount
        self.available -= amount

    def release(self, amount: int) -> None:
        self.reserved -= amount
        self.available += amount

    def add_product(self, amount: int) -> None:
        self.available += amount

    def buy(self, amount: int) -> None:
        self.available -= amount

@dataclass
class Sale:
    data: datetime
    category: str
    product_name: str
    attribute: str
    amount: int
    total: float

    def __str__(self):
        attribute = CONFIG.ATTRIBUTE_MAP.get(CONFIG.PRODUCT_CATEGORIES[self.category])
        attribute_emoji = CONFIG.ATTRIBUTE_EMOJIS.get(attribute)
        return (
            f"📅 Дата: {self.data.strftime('%d.%m.%Y %H:%M')}\n"
            f"📂 Категория: {self.category}\n"
            f"🏷️ Товар: {self.product_name}\n"
            f"{attribute_emoji} {attribute.title()}: {self.attribute}\n"
            f"📦 Количество: {self.amount} шт.\n"
            f"💰 Сумма: {self.total} грн"
        )
