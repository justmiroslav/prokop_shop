from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from database.session import Session
from repository.product_repository import ProductRepository
from repository.order_repository import OrderRepository
from repository.sheets import SheetManager
from service.product_service import ProductService
from service.order_service import OrderService

class DependencyMiddleware(BaseMiddleware):
    def __init__(self, sheet_manager: SheetManager):
        super().__init__()
        self.sheet_manager = sheet_manager

    async def __call__(self, handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery, data: Dict[str, Any]) -> Any:

        session = Session()

        try:
            product_repo = ProductRepository(session)
            order_repo = OrderRepository(session)

            product_service = ProductService(product_repo, self.sheet_manager)
            order_service = OrderService(order_repo, product_service)

            data.update({
                "session": session,
                "product_repo": product_repo,
                "order_repo": order_repo,
                "sheet_manager": self.sheet_manager,
                "product_service": product_service,
                "order_service": order_service
            })

            return await handler(event, data)
        finally:
            session.close()
