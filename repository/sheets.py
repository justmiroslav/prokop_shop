import gspread, logging, asyncio, uuid
from google.oauth2.service_account import Credentials
from typing import Optional, List
from datetime import datetime

from utils.config import CONFIG
from utils.models import Product, Sale, Order

class SheetManager:
    def __init__(self):
        self.client = self.get_client()
        self.sheet = self.client.open_by_key(CONFIG.SHEET_ID)
        self.product_sheets = None
        self.product_sheet_data = None
        self.periodic_refresh_task = None

        self.sales: dict[str, Sale] = {}
        self.sales_sheet = self.sheet.worksheet(CONFIG.SHEET_SALES)
        self.orders: dict[str, Order] = {}
        self.orders_sheet = self.sheet.worksheet(CONFIG.SHEET_ORDERS)
        self.get_fresh_data()

    @staticmethod
    def get_client() -> gspread.Client:
        """Get Google Sheets client"""
        creds = Credentials.from_service_account_file(CONFIG.CREDENTIALS_FILE, scopes=CONFIG.SCOPES)
        return gspread.authorize(creds)

    def get_fresh_data(self):
        """Get fresh data from Google Sheets"""
        try:
            self.product_sheets = {sheet.title: sheet for sheet in self.sheet.worksheets() if
                                   sheet.title not in CONFIG.EXCLUDED_SHEETS}
            self.product_sheet_data = {sheet: self.get_product_sheet_data(sheet) for sheet in
                                       self.product_sheets.keys()}
            self.map_categories_attribute()
            self.load_sales()
            self.load_orders()
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
                if len(row) < CONFIG.COL_PRICE + 1:
                    continue
                products[str(i)] = Product(row=i,
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

    def load_sales(self) -> None:
        """Load sales from the sales sheet"""
        try:
            sales_data = self.sales_sheet.get_all_values()

            if len(sales_data) <= 1:
                return

            for row in sales_data[1:]:
                if len(row) < 5:
                    continue
                name, attribute = row[2].split(" (")
                sale = Sale(id=row[0], category=row[1], product_name=name,
                    attribute=attribute[:-1], amount=int(row[3]), price=float(row[4]))
                self.sales[row[0]] = sale
        except Exception as e:
            logging.error(f"Error loading sales: {e}")

    def load_orders(self) -> None:
        """Load orders from the orders sheet"""
        try:
            orders_data = self.orders_sheet.get_all_values()

            if len(orders_data) <= 1:
                return

            for i, row in enumerate(orders_data[1:], start=2):
                if len(row) < 4:
                    continue
                order_id = row[0]
                order = Order(row=i, id=order_id, date=datetime.strptime(row[1], "%d.%m.%Y %H:%M:%S"), sales=[])
                self.orders[order_id] = order

                sales_ids = row[3].split(", ")
                for sale_id in sales_ids:
                    sale = self.sales.get(sale_id)
                    if sale:
                        order.sales.append(sale)
        except Exception as e:
            logging.error(f"Error loading orders: {e}")

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
        return {product.name for product in self.product_sheet_data[sheet_name].values() if
                self.get_condition(action, product)}

    def get_product_attributes(self, sheet_name: str, product_name: str, action: str) -> list[str]:
        """Get all product attributes from a specific category"""
        return [product.attribute for product in self.product_sheet_data[sheet_name].values() if
                product.name == product_name and self.get_condition(action, product)]

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
        return next(
            (product for product in products if product.name == product_name and product.attribute == attribute), None)

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

    def buy_product_amount(self, sheet_name: str, product: Product, amount: int, order_id: Optional[str] = None) -> Sale:
        """Buy a product and return the sale object"""
        product.buy(amount)
        self.update_product(sheet_name, product)
        return self.record_sale(sheet_name, product, amount, order_id)

    def record_sale(self, sheet_name: str, product: Product, amount: int, order_id: Optional[str] = None) -> Sale:
        """Record a sale and return the sale object"""
        sales_data = self.sales_sheet.get_all_values()

        first_row = sales_data[0] if sales_data else []
        if not first_row or first_row[0] != "ID":
            if sales_data:
                self.sales_sheet.clear()
            self.sales_sheet.append_row(["ID", "Категория", "Товар", "Количество", "Цена"])

        sale_id = str(uuid.uuid4())[:8]
        sale = Sale(id=sale_id, category=sheet_name, product_name=product.name, attribute=product.attribute,
            amount=amount, price=product.price, order_id=order_id)

        self.sales[sale_id] = sale
        self.sales_sheet.append_row([sale_id, sheet_name, sale.full_name, amount, product.price])
        return sale

    def create_order(self, sales: List[Sale]) -> Order:
        """Create a new order with the given sales"""
        orders_data = self.orders_sheet.get_all_values()

        first_row = orders_data[0] if orders_data else []
        if not first_row or first_row[0] != "ID":
            if orders_data:
                self.orders_sheet.clear()
            self.orders_sheet.append_row(["ID", "Дата", "Сума", "Товары"])
            row_index = 2
        else:
            row_index = len(orders_data) + 1

        order_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now()
        order = Order(row=row_index, id=order_id, date=timestamp, sales=sales)

        for sale in sales:
            sale.order_id = order_id
            self.sales[sale.id] = sale

        self.orders[order_id] = order
        self.orders_sheet.append_row([order_id, timestamp.strftime("%d.%m.%Y %H:%M:%S"), order.total,
            ", ".join([f"{sale.id}" for sale in sales])])
        return order

    def add_to_order(self, order_id: str, sale: Sale) -> Optional[Order]:
        """Add a sale to an existing order"""
        order = self.orders.get(order_id)
        if not order:
            return None

        sale.order_id = order_id
        self.sales[sale.id] = sale

        order.sales.append(sale)
        self.orders[order_id] = order

        self.orders_sheet.update_cell(order.row, 3, order.total)
        self.orders_sheet.update_cell(order.row, 4, ", ".join(sale.id for sale in order.sales))
        return order

    def get_sale_by_id(self, sale_id: str) -> Optional[Sale]:
        """Get sale by ID"""
        return self.sales.get(sale_id)

    def get_all_order_ids(self) -> list[str]:
        return list(self.orders.keys())

    def get_orders_by_date(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """Get orders between two dates from cache"""
        return [order for order in self.orders.values() if start_date <= order.date <= end_date]

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
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {e}")
