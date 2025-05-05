from typing import List, Optional
from database.models import Product
from repository.product_repository import ProductRepository
from repository.sheets import SheetManager

class ProductService:
    def __init__(self, product_repo: ProductRepository, sheet_manager: SheetManager):
        self.product_repo = product_repo
        self.sheet_manager = sheet_manager

    def get_categories(self) -> List[str]:
        """Get all available product categories"""
        return self.product_repo.get_unique_categories()

    def get_product_names(self, category: str, action: str = None) -> List[str]:
        """Get product names in a category"""
        return self.product_repo.get_unique_product_names(category,  action == "add")

    def get_attributes(self, category: str, product_name: str, action: str) -> List[str]:
        """Get all attributes for a product that have quantity > 0"""
        return self.product_repo.get_attributes_by_product(category, product_name, action == "add")

    def get_product(self, category: str, product_name: str, attribute: str) -> Optional[Product]:
        """Find a product by category, name and attribute"""
        return self.product_repo.get_by_name_attribute(category, product_name, attribute)

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return self.product_repo.get_by_id(product_id)

    def add_quantity(self, product: Product, amount: int) -> bool:
        """Add quantity to a product"""
        new_quantity = product.quantity + amount
        return self.sheet_manager.update_product_quantity(product, new_quantity)

    def remove_quantity(self, product: Product, amount: int) -> bool:
        """Remove quantity from a product"""
        if product.quantity < amount:
            return False

        new_quantity = product.quantity - amount
        return self.sheet_manager.update_product_quantity(product, new_quantity)
