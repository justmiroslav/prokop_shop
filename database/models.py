from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class OrderStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sheet_name = Column(String, nullable=False)
    sheet_row = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    attribute = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    is_archived = Column(Boolean, default=False)

    order_items = relationship("OrderItem", back_populates="product")

    @property
    def full_name(self):
        return f"{self.name} ({self.attribute})"

    def __repr__(self):
        return f"<Product {self.name} ({self.attribute})>"

class ProfitAdjustment(Base):
    __tablename__ = "profit_adjustments"

    id = Column(Integer, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    affects_total = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    order = relationship("Order", back_populates="adjustments")

    def __repr__(self):
        prefix = "+" if self.amount > 0 else ""
        return f"<Adjustment {prefix}{self.amount} грн: {self.reason}>"

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    adjustments = relationship("ProfitAdjustment", back_populates="order", cascade="all, delete-orphan")

    @property
    def display_name(self):
        return self.name or self.id

    @property
    def total_items(self):
        return sum(item.price * item.quantity for item in self.items)

    @property
    def total_adjustments(self):
        return sum(adj.amount for adj in self.adjustments if adj.affects_total)

    @property
    def total_profit_adjustments(self):
        return sum(adj.amount for adj in self.adjustments)

    @property
    def total(self):
        return self.total_items + self.total_adjustments

    @property
    def total_cost(self):
        return sum(item.cost * item.quantity for item in self.items)

    @property
    def profit(self):
        return self.total_items - self.total_cost + self.total_profit_adjustments

    @property
    def discount(self):
        return sum(adj.amount for adj in self.adjustments if adj.affects_total and adj.amount < 0)

    def __repr__(self):
        return f"<Order {self.display_name} ({self.status.value})>"

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    @property
    def display_name(self):
        """Возвращает название товара"""
        if self.product_name:
            return self.product_name
        elif self.product:
            return self.product.full_name
        else:
            return "Неизвестный товар"

    def __repr__(self):
        return f"<OrderItem {self.display_name} x{self.quantity}>"
