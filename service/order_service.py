from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

from database.models import Order, OrderItem, Product, OrderStatus
from repository.order_repository import OrderRepository
from service.product_service import ProductService

class OrderService:
    def __init__(self, order_repo: OrderRepository, product_service: ProductService):
        self.order_repo = order_repo
        self.product_service = product_service

    def create_order(self) -> Order:
        """Create a new pending order"""
        return self.order_repo.create_order()

    def get_active_orders(self) -> List[Order]:
        """Get all active (pending) orders"""
        return self.order_repo.get_active_orders()

    def get_active_order_ids(self) -> List[str]:
        """Get IDs of all active orders"""
        return self.order_repo.get_active_order_ids()

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID"""
        return self.order_repo.get_by_id(order_id)

    def get_order_item(self, item_id: int) -> Optional[OrderItem]:
        """Get an order item by ID"""
        return self.order_repo.get_order_item(item_id)

    def add_product_to_order(self, order: Order, product: Product, quantity: int) -> Tuple[
        bool, Optional[OrderItem], str]:
        """Add a product to an order, reducing product quantity"""
        if order.status != OrderStatus.PENDING:
            return False, None, "Заказ уже завершен"

        if product.quantity < quantity:
            return False, None, f"Недостаточно товара в наличии. Доступно: {product.quantity}"

        # Reduce product quantity
        success = self.product_service.remove_quantity(product, quantity)
        if not success:
            return False, None, "Ошибка при обновлении количества товара"

        # Add to order
        order_item = self.order_repo.add_item(
            order, product.id, quantity, product.price, product.cost
        )

        return True, order_item, "Товар успешно добавлен в заказ"

    def update_order_item_quantity(self, item: OrderItem, new_quantity: int) -> Tuple[bool, str]:
        """Update order item quantity"""
        if item.order.status != OrderStatus.PENDING:
            return False, "Заказ уже завершен"

        product = self.product_service.get_product_by_id(item.product_id)
        if not product:
            return False, "Товар не найден"

        quantity_diff = new_quantity - item.quantity

        if quantity_diff > 0:
            if product.quantity < quantity_diff:
                return False, f"Недостаточно товара в наличии. Доступно: {product.quantity}"

            success = self.product_service.remove_quantity(product, quantity_diff)
            if not success:
                return False, "Ошибка при обновлении количества товара"
        elif quantity_diff < 0:
            success = self.product_service.add_quantity(product, abs(quantity_diff))
            if not success:
                return False, "Ошибка при обновлении количества товара"

        if new_quantity <= 0:
            self.order_repo.remove_item(item)
            return True, "Товар удален из заказа"
        else:
            self.order_repo.update_item_quantity(item, new_quantity)
            return True, "Количество товара обновлено"

    def remove_order_item(self, item: OrderItem) -> Tuple[bool, str]:
        """Remove an item from order"""
        if item.order.status != OrderStatus.PENDING:
            return False, "Заказ уже завершен"

        product = self.product_service.get_product_by_id(item.product_id)
        if not product:
            return False, "Товар не найден"

        success = self.product_service.add_quantity(product, item.quantity)
        if not success:
            return False, "Ошибка при возврате товара в наличие"

        self.order_repo.remove_item(item)
        return True, "Товар удален из заказа"

    def complete_order(self, order: Order) -> Tuple[bool, str]:
        """Complete an order"""
        if order.status != OrderStatus.PENDING:
            return False, "Заказ уже завершен"

        if not order.items:
            return False, "Невозможно завершить пустой заказ"

        self.order_repo.complete_order(order)
        return True, "Заказ успешно завершен"

    def delete_order(self, order: Order) -> Tuple[bool, str]:
        """Delete an order and return products to inventory"""
        if order.status != OrderStatus.PENDING:
            return False, "Невозможно удалить завершенный заказ"

        for item in order.items:
            product = self.product_service.get_product_by_id(item.product_id)
            if product:
                self.product_service.add_quantity(product, item.quantity)

        self.order_repo.delete_order(order)
        return True, "Заказ успешно удален"

    def get_statistics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get order statistics for a period"""
        orders = self.order_repo.get_completed_orders_by_period(start_date, end_date)

        total_revenue = sum(order.total for order in orders)
        total_cost = sum(order.total_cost for order in orders)
        profit = total_revenue - total_cost

        return {
            "orders": orders,
            "count": len(orders),
            "gross_revenue": total_revenue,
            "net_profit": profit
        }

    @staticmethod
    def get_date_period(period: str) -> Tuple[datetime, datetime, str]:
        """Get start and end dates for a period"""
        now = datetime.now()

        if period == "today":
            start_date = datetime(now.year, now.month, now.day)
            end_date = now
            name = "сегодня"
        elif period == "yesterday":
            yesterday = now - timedelta(days=1)
            start_date = datetime(yesterday.year, yesterday.month, yesterday.day)
            end_date = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
            name = "вчера"
        elif period == "week":
            start_of_week = now - timedelta(days=now.weekday())
            start_date = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
            end_date = now
            name = "эта неделя"
        elif period == "month":
            start_date = datetime(now.year, now.month, 1)
            end_date = now
            name = "этот месяц"
        else:
            raise ValueError("Invalid period")

        return start_date, end_date, name
