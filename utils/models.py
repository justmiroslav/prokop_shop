from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

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
        if not self.reserved:
            self.available -= amount
        else:
            to_release = min(self.reserved, amount)
            self.reserved -= to_release
            if self.reserved == 0:
                self.available -= amount - to_release

@dataclass
class Sale:
    id: str
    category: str
    product_name: str
    attribute: str
    amount: int
    price: float
    order_id: Optional[str] = None

    @property
    def total(self) -> float:
        return self.amount * self.price

    @property
    def full_name(self) -> str:
        return f"{self.product_name} ({self.attribute})"

    def __str__(self):
        return (
            f"🏷️ Товар: {self.full_name}\n📦 Количество: {self.amount} шт, Цена: {self.price} грн\n"
        )

@dataclass
class Order:
    row: int
    id: str
    date: datetime
    sales: list[Sale] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(sale.total for sale in self.sales)

    def __str__(self):
        return (
            f"🛒 Заказ № {self.id}\n"
            f"📅 Дата: {self.date.strftime("%d.%m.%Y %H:%M:%S")}\n"
            f"💰 Сумма заказа: {self.total} грн"
        )
