from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
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

    order_items = relationship("OrderItem", back_populates="product")

    @property
    def full_name(self):
        return f"{self.name} ({self.attribute})"

    def __repr__(self):
        return f"<Product {self.name} ({self.attribute})>"

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)  # UUID
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def total(self):
        return sum(item.price * item.quantity for item in self.items)

    @property
    def total_cost(self):
        return sum(item.cost * item.quantity for item in self.items)

    @property
    def profit(self):
        return self.total - self.total_cost

    def __repr__(self):
        return f"<Order {self.id} ({self.status.value})>"

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.product_id} x{self.quantity}>"
