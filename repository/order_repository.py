from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from database.models import Order, OrderItem, OrderStatus

class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[Order]:
        """Get all orders"""
        return self.session.query(Order).all()

    def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.session.query(Order).filter(Order.id == order_id).first()

    def get_active_orders(self) -> List[Order]:
        """Get all active (pending) orders"""
        return self.session.query(Order).filter(Order.status == OrderStatus.PENDING).all()

    def get_active_order_ids(self) -> List[str]:
        """Get all active order IDs"""
        return [order.id for order in self.session.query(Order.id).filter(
            Order.status == OrderStatus.PENDING
        ).all()]

    def get_completed_orders(self) -> List[Order]:
        """Get all completed orders"""
        return self.session.query(Order).filter(Order.status == OrderStatus.COMPLETED).all()

    def get_completed_orders_by_period(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """Get completed orders between two dates"""
        return self.session.query(Order).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at.between(start_date, end_date)
        ).all()

    def create_order(self) -> Order:
        """Create a new pending order"""
        order = Order(id=str(uuid.uuid4())[:8])
        self.session.add(order)
        self.session.commit()
        return order

    def add_item(self, order: Order, product_id: int, quantity: int, price: float, cost: float) -> OrderItem:
        """Add item to order"""
        existing_item = self.session.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.product_id == product_id
        ).first()

        if existing_item:
            existing_item.quantity += quantity
            item = existing_item
        else:
            item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                price=price,
                cost=cost
            )
            self.session.add(item)

        self.session.commit()
        return item

    def update_item_quantity(self, item: OrderItem, quantity: int) -> OrderItem:
        """Update order item quantity"""
        item.quantity = quantity
        self.session.commit()
        return item

    def remove_item(self, item: OrderItem) -> None:
        """Remove item from order"""
        self.session.delete(item)
        self.session.commit()

    def complete_order(self, order: Order) -> Order:
        """Complete an order"""
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now()
        self.session.commit()
        return order

    def delete_order(self, order: Order) -> None:
        """Delete an order"""
        self.session.delete(order)
        self.session.commit()

    def get_order_items(self, order_id: str) -> List[OrderItem]:
        """Get all items in an order"""
        return self.session.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    def get_order_item(self, item_id: int) -> Optional[OrderItem]:
        """Get order item by ID"""
        return self.session.query(OrderItem).filter(OrderItem.id == item_id).first()
