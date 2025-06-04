from typing import List, Optional
from database.models import Product
from repository.product_repository import ProductRepository
from repository.sheets import SheetManager

class ProductService:
    def __init__(self, product_repo: ProductRepository, sheet_manager: SheetManager):
        self.product_repo = product_repo
        self.sheet_manager = sheet_manager

    def get_categories(self) -> List[str]:
        return self.product_repo.get_unique_categories()

    def get_product_names(self, category: str, action: str = None) -> List[str]:
        return self.product_repo.get_unique_product_names(category,  action == "add")

    def get_attributes(self, category: str, product_name: str, action: str) -> List[str]:
        return self.product_repo.get_attributes_by_product(category, product_name, action == "add")

    def get_product(self, category: str, product_name: str, attribute: str) -> Optional[Product]:
        return self.product_repo.get_by_name_attribute(category, product_name, attribute)

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        return self.product_repo.get_by_id(product_id)

    def add_quantity(self, product: Product, amount: int) -> bool:
        return self.sheet_manager.queue_quantity_update(product, product.quantity + amount)

    def remove_quantity(self, product: Product, amount: int) -> bool:
        return self.sheet_manager.queue_quantity_update(product, product.quantity - amount)

    def update_quantity(self, product: Product, new_quantity: int) -> bool:
        return self.sheet_manager.queue_quantity_update(product, new_quantity)
