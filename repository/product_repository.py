from sqlalchemy.orm import Session
from typing import List, Optional

from database.models import Product

class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return self.session.query(Product).filter(Product.id == product_id).first()

    def get_by_name_attribute(self, sheet_name: str, name: str, attribute: str) -> Optional[Product]:
        """Get product by category, name and attribute"""
        return self.session.query(Product).filter(
            Product.sheet_name == sheet_name,
            Product.name == name,
            Product.attribute == attribute
        ).first()

    def create(self, product: Product) -> Product:
        """Create a new product"""
        self.session.add(product)
        self.session.commit()
        return product

    def update(self, product: Product) -> Product:
        """Update a product"""
        self.session.merge(product)
        self.session.commit()
        return product

    def get_unique_categories(self) -> List[str]:
        """Get all unique product categories (excluding archived)"""
        return [r[0] for r in self.session.query(Product.sheet_name).filter(
            Product.is_archived == False).distinct()]

    def get_unique_product_names(self, category: str, include_zero_qty: bool = False) -> List[str]:
        """Get all unique product names in a category"""
        query = self.session.query(Product.name).filter(
            Product.sheet_name == category,
            Product.is_archived == False
        )

        if not include_zero_qty:
            query = query.filter(Product.quantity > 0)

        return [r[0] for r in query.distinct()]

    def get_attributes_by_product(self, category: str, product_name: str, include_zero_qty: bool = False) -> List[str]:
        """Get all attributes for a product"""
        query = self.session.query(Product.attribute).filter(
            Product.sheet_name == category,
            Product.name == product_name,
            Product.is_archived == False
        )

        if not include_zero_qty:
            query = query.filter(Product.quantity > 0)

        return [r[0] for r in query]

    def get_all_by_sheet(self, sheet_name: str) -> List[Product]:
        """Get all products from specific sheet"""
        return self.session.query(Product).filter(Product.sheet_name == sheet_name and Product.is_archived == False).all()

    def archive_product(self, product: Product) -> Product:
        """Archive a product"""
        product.is_archived = True
        return self.update(product)

    def unarchive_product(self, product: Product) -> Product:
        """Unarchive a product"""
        product.is_archived = False
        return self.update(product)
