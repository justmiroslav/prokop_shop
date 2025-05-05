from sqlalchemy.orm import Session
from typing import List, Optional

from database.models import Product

class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[Product]:
        """Get all products"""
        return self.session.query(Product).all()

    def get_by_category(self, category: str) -> List[Product]:
        """Get products by category"""
        return self.session.query(Product).filter(Product.sheet_name == category).all()

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return self.session.query(Product).filter(Product.id == product_id).first()

    def get_by_sheet_info(self, sheet_name: str, row: int) -> Optional[Product]:
        """Get product by sheet name and row"""
        return self.session.query(Product).filter(
            Product.sheet_name == sheet_name,
            Product.sheet_row == row
        ).first()

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

    def delete(self, product: Product) -> None:
        """Delete a product"""
        self.session.delete(product)
        self.session.commit()

    def get_unique_categories(self) -> List[str]:
        """Get all unique product categories"""
        return [r[0] for r in self.session.query(Product.sheet_name).distinct()]

    def get_unique_product_names(self, category: str) -> List[str]:
        """Get all unique product names in a category with quantity > 0"""
        return [r[0] for r in self.session.query(Product.name).filter(
            Product.sheet_name == category,
            Product.quantity > 0
        ).distinct()]

    def get_attributes_by_product(self, category: str, product_name: str) -> List[str]:
        """Get all attributes for a product with quantity > 0"""
        return [r[0] for r in self.session.query(Product.attribute).filter(
            Product.sheet_name == category,
            Product.name == product_name,
            Product.quantity > 0
        )]
