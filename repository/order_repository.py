from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from database.models import Order, OrderItem, OrderStatus, ProfitAdjustment

class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.session.query(Order).filter(Order.id == order_id).first()

    def get_active_order_ids(self) -> List[str]:
        """Get all active order IDs"""
        return [order.id for order in self.session.query(Order.id).filter(
            Order.status == OrderStatus.PENDING
        ).all()]

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

    def add_item(self, order: Order, product_id: int, quantity: int, price: float, cost: float) -> None:
        """Add item to order"""
        existing_item = self.session.query(OrderItem).filter(
            OrderItem.order_id == order.id,
            OrderItem.product_id == product_id
        ).first()

        if existing_item:
            existing_item.quantity += quantity
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

    def update_item_quantity(self, item: OrderItem, quantity: int) -> OrderItem:
        """Update order item quantity"""
        item.quantity = quantity
        self.session.commit()
        return item

    def remove_item(self, item: OrderItem) -> None:
        """Remove item from order"""
        self.session.delete(item)
        self.session.commit()

    def complete_order(self, order: Order, completion_date: datetime = None) -> Order:
        """Complete an order with optional specific date"""
        order.status = OrderStatus.COMPLETED
        order.completed_at = completion_date or datetime.now()
        self.session.commit()
        return order

    def delete_order(self, order: Order) -> None:
        """Delete an order"""
        self.session.delete(order)
        self.session.commit()

    def get_order_item(self, item_id: int) -> Optional[OrderItem]:
        """Get order item by ID"""
        return self.session.query(OrderItem).filter(OrderItem.id == item_id).first()

    def add_profit_adjustment(self, order: Order, amount: float, reason: str) -> ProfitAdjustment:
        """Add profit adjustment to order"""
        adjustment = ProfitAdjustment(
            order_id=order.id,
            amount=amount,
            reason=reason
        )
        self.session.add(adjustment)
        self.session.commit()
        return adjustment

    def get_profit_adjustments(self, order_id: str) -> List[ProfitAdjustment]:
        """Get all profit adjustments for an order"""
        return self.session.query(ProfitAdjustment).filter(
            ProfitAdjustment.order_id == order_id
        ).order_by(ProfitAdjustment.created_at).all()

    def delete_profit_adjustment(self, adjustment_id: int) -> None:
        """Delete a profit adjustment"""
        adjustment = self.session.query(ProfitAdjustment).filter(
            ProfitAdjustment.id == adjustment_id
        ).first()

        if adjustment:
            self.session.delete(adjustment)
            self.session.commit()
