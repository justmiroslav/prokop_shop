from sqlalchemy.orm import Session
from typing import List, Optional, Set, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy import extract
import uuid

from database.models import Order, OrderItem, OrderStatus, ProfitAdjustment

class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.session.query(Order).filter(Order.id == order_id).first()

    def get_active_order_names_list(self) -> List[str]:
        """Get names of active orders only"""
        return [order.name for order in self.session.query(Order.name).filter(
            Order.status == OrderStatus.PENDING,
            Order.name.isnot(None)
        ).all()]

    def get_active_order_names(self) -> List[Tuple[str, str]]:
        """Get names of all active orders"""
        active_orders = self.session.query(Order).filter(
            Order.status == OrderStatus.PENDING
        ).all()
        return [(order.id, order.display_name) for order in active_orders]

    def get_completed_dates(self, days_limit: int) -> Set[date]:
        """Get set of dates when orders were completed within the last N days"""
        date_limit = datetime.now() - timedelta(days=days_limit)
        completed_orders = self.session.query(Order.completed_at).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at >= date_limit
        ).all()

        return {order.completed_at.date() for order in completed_orders if order.completed_at}

    def get_completed_order_names_by_date(self, date_value: date) -> List[Tuple[str, str]]:
        """Get completed orders with display names by date (id, display_name)"""
        next_day = datetime.combine(date_value, datetime.min.time()) + timedelta(days=1)
        day_start = datetime.combine(date_value, datetime.min.time())

        valid_orders = self.session.query(Order).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at >= day_start,
            Order.completed_at < next_day
        ).all()

        return [(order.id, order.display_name) for order in valid_orders]

    def get_months_with_completed_orders(self) -> List[Tuple[int, int]]:
        """Get months with completed orders (year, month)"""
        result = self.session.query(
            extract('year', Order.completed_at).label('year'),
            extract('month', Order.completed_at).label('month')
        ).filter(
            Order.status == OrderStatus.COMPLETED,
            Order.completed_at.isnot(None)
        ).distinct().all()

        return [(int(r.year), int(r.month)) for r in result]

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

    def update_order_name(self, order: Order, name: str) -> Order:
        """Update order name"""
        order.name = name
        self.session.commit()
        return order

    def add_item(self, order: Order, product_id: int, quantity: int, price: float, cost: float,
                 product_name: str = None) -> None:
        """Add item to order with product name"""
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
                product_name=product_name,
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

    def restore_order(self, order: Order) -> Order:
        """Restore a completed order to pending state"""
        order.status = OrderStatus.PENDING
        order.completed_at = None
        self.session.commit()
        return order

    def delete_order(self, order: Order) -> None:
        """Delete an order"""
        self.session.delete(order)
        self.session.commit()

    def get_order_item(self, item_id: int) -> Optional[OrderItem]:
        """Get order item by ID"""
        return self.session.query(OrderItem).filter(OrderItem.id == item_id).first()

    def add_profit_adjustment(self, order: Order, amount: float, reason: str, affects_total: bool = True, profit_amount: float = None) -> ProfitAdjustment:
        """Add profit adjustment to order"""
        adjustment = ProfitAdjustment(
            order_id=order.id,
            amount=amount,
            profit_amount=profit_amount,
            reason=reason,
            affects_total=affects_total
        )
        self.session.add(adjustment)
        self.session.commit()
        return adjustment

    def get_profit_adjustments(self, order_id: str) -> List[ProfitAdjustment]:
        """Get all profit adjustments for an order"""
        return self.session.query(ProfitAdjustment).filter(
            ProfitAdjustment.order_id == order_id
        ).order_by(ProfitAdjustment.created_at).all()

    def get_profit_adjustment(self, adjustment_id: int) -> Optional[ProfitAdjustment]:
        """Get profit adjustment by ID"""
        return self.session.query(ProfitAdjustment).filter(
            ProfitAdjustment.id == adjustment_id
        ).first()

    def delete_profit_adjustment(self, adjustment_id: int) -> None:
        """Delete a profit adjustment"""
        adjustment = self.session.query(ProfitAdjustment).filter(
            ProfitAdjustment.id == adjustment_id
        ).first()

        if adjustment:
            self.session.delete(adjustment)
            self.session.commit()
