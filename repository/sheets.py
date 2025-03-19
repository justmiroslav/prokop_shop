import gspread, logging, asyncio
from google.oauth2.service_account import Credentials
from typing import Optional, Callable
from datetime import datetime

from utils.config import CONFIG
from utils.models import Product, Sale

class SheetManager:
    def __init__(self):
        self.client = self.get_client()
        self.sheet = self.client.open_by_key(CONFIG.SHEET_ID)
        self.product_sheets = None
        self.product_sheet_data = None
        self.periodic_refresh_task = None
        self.get_fresh_data()

    @staticmethod
    def get_client() -> gspread.Client:
        """Get Google Sheets client"""
        creds = Credentials.from_service_account_file(CONFIG.CREDENTIALS_FILE, scopes=CONFIG.SCOPES)
        return gspread.authorize(creds)

    def get_fresh_data(self):
        """Get fresh data from Google Sheets"""
        try:
            self.product_sheets = {sheet.title: sheet for sheet in self.sheet.worksheets() if sheet.title not in CONFIG.EXCLUDED_SHEETS}
            self.product_sheet_data = {sheet: self.get_product_sheet_data(sheet) for sheet in self.product_sheets.keys()}
            self.map_categories_attribute()
        except Exception as e:
            logging.error(f"Error refreshing data: {e}")

    def map_categories_attribute(self) -> None:
        """Map categories to attributes"""
        for sheet_name, worksheet in self.product_sheets.items():
            header = worksheet.row_values(1)
            CONFIG.PRODUCT_CATEGORIES[sheet_name] = header[CONFIG.COL_ATTRIBUTE]

    def get_product_sheet_data(self, sheet_name: str) -> dict[str, Product]:
        """Get all products from a specific category"""
        try:
            worksheet = self.product_sheets[sheet_name]
            data = worksheet.get_all_values()

            products: dict[str, Product] = {}
            for i, row in enumerate(data[1:], start=2):
                products[str(i)] = Product(
                    row=i,
                    name=row[CONFIG.COL_PRODUCT],
                    attribute=row[CONFIG.COL_ATTRIBUTE],
                    available=int(row[CONFIG.COL_AVAILABLE]),
                    reserved=int(row[CONFIG.COL_RESERVED]),
                    price=float(row[CONFIG.COL_PRICE])
                )

            return products
        except Exception as e:
            logging.error(f"Error getting products: {e}")
            return {}

    @staticmethod
    def get_condition(action: str, product: Product) -> bool:
        """Get conditions for product selection"""
        if action == "release":
            return product.reserved > 0
        elif action == "buy":
            return (product.available + product.reserved) > 0
        elif action == "reserve":
            return product.available > 0
        else:
            return True

    def get_product_names(self, sheet_name: str, action: str) -> set[str]:
        """Get unique product names that have at least one variant meeting the condition"""
        return {product.name for product in self.product_sheet_data[sheet_name].values() if self.get_condition(action, product)}

    def get_product_attributes(self, sheet_name: str, product_name: str, action: str) -> list[str]:
        """Get all product attributes from a specific category"""
        return [product.attribute for product in self.product_sheet_data[sheet_name].values() if product.name == product_name and self.get_condition(action, product)]

    def update_product(self, sheet_name: str, product: Product, update_sec: bool = True) -> None:
        """Update a product cell"""
        worksheet = self.product_sheets[sheet_name]
        worksheet.update_cell(product.row, CONFIG.COL_AVAILABLE + 1, product.available)
        if update_sec:
            worksheet.update_cell(product.row, CONFIG.COL_RESERVED + 1, product.reserved)
        self.product_sheet_data[sheet_name][str(product.row)] = product

    def find_product(self, sheet_name: str, product_name: str, attribute: str) -> Optional[Product]:
        """Find a product by name and attribute"""
        products = self.product_sheet_data[sheet_name].values()
        return next((product for product in products if product.name == product_name and product.attribute == attribute), None)

    def reserve_product_amount(self, sheet_name: str, product: Product, amount: int):
        """Reserve a product"""
        product.reserve(amount)
        self.update_product(sheet_name, product)

    def release_product_amount(self, sheet_name: str, product: Product, amount: int) -> None:
        """Release a product"""
        product.release(amount)
        self.update_product(sheet_name, product)

    def add_product_amount(self, sheet_name: str, product: Product, amount: int) -> None:
        """Add a product"""
        product.add_product(amount)
        self.update_product(sheet_name, product, update_sec=False)

    def buy_product_amount(self, sheet_name: str, product: Product, amount: int) -> None:
        """Buy a product"""
        product.buy(amount)
        self.update_product(sheet_name, product)
        self.record_sale(sheet_name, product, amount)

    def record_sale(self, sheet_name: str, product: Product, amount: int) -> None:
        """Record a sale"""
        sales_sheet = self.sheet.worksheet(CONFIG.SHEET_SALES)
        sales_data = sales_sheet.get_all_values()

        first_row = sales_data[0] if sales_data else []
        if not first_row or first_row[0] != "Дата":
            if sales_data:
                sales_sheet.clear()
            sales_sheet.append_row(["Дата", "Категорія", "Товар", CONFIG.PRODUCT_CATEGORIES[sheet_name], "Кількість", "Сума"])

        sales_sheet.append_row([
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            sheet_name,
            product.name,
            product.attribute,
            amount,
            amount * product.price
        ])

    def get_filtered_sales(self, filter_func: Callable[[Sale], bool]) -> list[Sale]:
        """Get filtered sales"""
        sales_sheet = self.sheet.worksheet(CONFIG.SHEET_SALES)
        sales_data = sales_sheet.get_all_values()

        if len(sales_data) <= 1:
            return []

        sales: list[Sale] = []
        for row in sales_data[1:]:
            sale = Sale(
                data=datetime.strptime(row[0], "%d.%m.%Y %H:%M:%S"),
                category=row[1],
                product_name=row[2],
                attribute=row[3],
                amount=int(row[4]),
                total=float(row[5])
            )
            if filter_func(sale):
                sales.append(sale)

        return sales

    def get_sales(self, start_date: datetime, end_date: datetime) -> list[Sale]:
        """Get sales between two dates"""
        return self.get_filtered_sales(lambda sale: start_date <= sale.data <= end_date)

    def get_sales_by_category(self, category: str) -> list[Sale]:
        """Get sales by category"""
        return self.get_filtered_sales(lambda sale: sale.category == category)

    async def start_periodic_refresh(self, interval_seconds=20):
        """Запустить задачу периодического обновления"""
        self.periodic_refresh_task = asyncio.create_task(self._periodic_refresh(interval_seconds))

    async def stop_periodic_refresh(self):
        """Остановить задачу периодического обновления"""
        if self.periodic_refresh_task:
            self.periodic_refresh_task.cancel()
            self.periodic_refresh_task = None

    async def _periodic_refresh(self, interval_seconds):
        """Периодически обновлять данные"""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                self.get_fresh_data()
                logging.info(f"Данные обновлены в {datetime.now()}")
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {e}")
