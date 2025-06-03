from typing import List, Optional, Dict, Tuple
from datetime import datetime, date

from database.models import Order, OrderItem, Product, ProfitAdjustment
from repository.order_repository import OrderRepository
from service.product_service import ProductService
from utils.shit_utils import get_date_range, format_customer_message, build_date_period, format_dates_with_orders

class OrderService:
    def __init__(self, order_repo: OrderRepository, product_service: ProductService):
        self.order_repo = order_repo
        self.product_service = product_service

    def create_order(self) -> Order:
        """Create a new pending order"""
        return self.order_repo.create_order()

    def get_active_order_names(self) -> List[Tuple[str, str]]:
        """Get names of all active orders"""
        return self.order_repo.get_active_order_names()

    def get_dates_with_completed_orders(self, days_limit: int = 3) -> List[Tuple[date, str]]:
        """Get dates when orders were completed within the last N days"""
        completed_dates = sorted(self.order_repo.get_completed_dates(days_limit))
        if completed_dates:
            return format_dates_with_orders(sorted(completed_dates, reverse=True))
        return []

    def get_completed_orders_display_names_by_date(self, date_value: date) -> List[Tuple[str, str]]:
        """Get completed orders with display names by date (id, display_name)"""
        return self.order_repo.get_completed_order_names_by_date(date_value)

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID"""
        return self.order_repo.get_by_id(order_id)

    def get_all_order_names(self) -> List[str]:
        """Get all order names"""
        return self.order_repo.get_all_order_names()

    def get_order_item(self, item_id: int) -> Optional[OrderItem]:
        """Get an order item by ID"""
        return self.order_repo.get_order_item(item_id)

    def update_order_name(self, order: Order, name: str) -> Order:
        """Update order name"""
        return self.order_repo.update_order_name(order, name)

    async def add_product_to_order(self, order: Order, product: Product, quantity: int) -> None:
        """Add a product to an order, reducing product quantity"""
        await self.product_service.remove_quantity(product, quantity)
        self.order_repo.add_item(order, product.id, quantity, product.price, product.cost)

    async def update_order_item_quantity(self, item: OrderItem, new_quantity: int) -> None:
        """Update order item quantity"""
        product = self.product_service.get_product_by_id(item.product_id)
        await self.product_service.update_quantity(product, product.quantity - (new_quantity - item.quantity))
        self.order_repo.update_item_quantity(item, new_quantity)

    async def remove_order_item(self, item: OrderItem) -> None:
        """Remove an item from order"""
        product = self.product_service.get_product_by_id(item.product_id)
        await self.product_service.add_quantity(product, item.quantity)
        self.order_repo.remove_item(item)

    def complete_order(self, order: Order, completion_date: datetime = None) -> Tuple[bool, str]:
        """Complete an order with optional custom completion date"""
        if not order.items:
            return False, "Невозможно завершить пустой заказ"

        if completion_date and completion_date.date() < order.created_at.date():
            return False, "Дата завершения не может быть раньше даты создания заказа"

        self.order_repo.complete_order(order, completion_date)
        return True, f"✅ Заказ {order.display_name} успешно завершен!"

    def restore_order(self, order: Order) -> str:
        """Restore a completed order to pending state"""
        self.order_repo.restore_order(order)
        return f"✅ Заказ {order.display_name} успешно активирован!"

    async def delete_order(self, order: Order) -> str:
        """Delete an order and return products to inventory"""
        for item in order.items:
            product = self.product_service.get_product_by_id(item.product_id)
            if product:
                await self.product_service.add_quantity(product, item.quantity)

        self.order_repo.delete_order(order)
        return f"🗑️ Заказ {order.display_name} успешно удален!"

    def get_statistics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get order statistics for a period"""
        orders = self.order_repo.get_completed_orders_by_period(start_date, end_date)

        total_sum = sum(order.total for order in orders)
        total_cost = sum(order.total_cost for order in orders)
        total_adjustments = sum(order.total_adjustments for order in orders)
        profit = sum(order.profit for order in orders)

        return {
            "orders": orders,
            "count": len(orders),
            "total_sum": total_sum,
            "total_cost": total_cost,
            "total_adjustments": total_adjustments,
            "net_profit": profit
        }

    def add_profit_adjustment(self, order: Order, amount: float, reason: str) -> None:
        """Add profit adjustment to order"""
        self.order_repo.add_profit_adjustment(order, amount, reason)

    def get_profit_adjustments(self, order_id: str) -> List[ProfitAdjustment]:
        """Get all profit adjustments for an order"""
        return self.order_repo.get_profit_adjustments(order_id)

    def delete_profit_adjustment(self, adjustment_id: int) -> None:
        """Delete a profit adjustment"""
        self.order_repo.delete_profit_adjustment(adjustment_id)

    @staticmethod
    def get_completion_date_options(order: Order) -> List[Tuple[date, str]]:
        """Get available completion date options"""
        return get_date_range(order)

    @staticmethod
    def get_customer_message(order: Order) -> str:
        """Format message for customer with order details"""
        return format_customer_message(order)

    @staticmethod
    def get_date_period(period: str) -> Tuple[datetime, datetime, str]:
        """Get start and end dates for a period"""
        return build_date_period(period)
