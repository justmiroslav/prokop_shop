import gspread, logging, asyncio
from google.oauth2.service_account import Credentials
from sqlalchemy.orm import Session

from utils.config import CONFIG
from database.models import Product
from repository.product_repository import ProductRepository

class SheetManager:
    def __init__(self, db_session: Session):
        self.client = self.get_client()
        self.sheet = self.client.open_by_key(CONFIG.SHEET_ID)
        self.product_sheets = {sheet.title: sheet for sheet in self.sheet.worksheets() if sheet.title != CONFIG.EXCLUDED_SHEET}
        self.product_repo = ProductRepository(db_session)
        self.db_session = db_session
        self.periodic_refresh_task = None
        for sheet_name, worksheet in self.product_sheets.items():
            header = worksheet.row_values(1)
            CONFIG.PRODUCT_CATEGORIES[sheet_name] = header[CONFIG.COL_ATTRIBUTE]

    @staticmethod
    def get_client() -> gspread.Client:
        """Get Google Sheets client"""
        creds = Credentials.from_service_account_file(CONFIG.CREDENTIALS_FILE, scopes=CONFIG.SCOPES)
        return gspread.authorize(creds)

    def sync_products(self):
        """Synchronize products from Google Sheets to the database"""
        try:
            for sheet_name, worksheet in self.product_sheets.items():
                self._sync_sheet_products(sheet_name, worksheet)

            logging.info("Products synchronized from Google Sheets")
        except Exception as e:
            logging.error(f"Error syncing products: {e}")

    def _sync_sheet_products(self, sheet_name: str, worksheet: gspread.Worksheet):
        """Sync products from a specific worksheet"""
        try:
            data = worksheet.get_all_values()
            if len(data) <= 1:
                return

            for i, row in enumerate(data[1:], start=2):
                if len(row) < CONFIG.COL_COST + 1:
                    continue

                try:
                    name = row[CONFIG.COL_PRODUCT]
                    attribute = row[CONFIG.COL_ATTRIBUTE]
                    quantity = int(row[CONFIG.COL_QUANTITY])
                    price = float(row[CONFIG.COL_PRICE])
                    cost = float(row[CONFIG.COL_COST])

                    product = self.product_repo.get_by_sheet_info(sheet_name, i)

                    if product:
                        if (product.name != name or
                                product.attribute != attribute or
                                product.quantity != quantity or
                                product.price != price or
                                product.cost != cost):

                            product.name = name
                            product.attribute = attribute
                            product.quantity = quantity
                            product.price = price
                            product.cost = cost
                            self.product_repo.update(product)
                    else:
                        product = Product(
                            sheet_name=sheet_name,
                            sheet_row=i,
                            name=name,
                            attribute=attribute,
                            quantity=quantity,
                            price=price,
                            cost=cost
                        )
                        self.product_repo.create(product)

                except (ValueError, IndexError) as e:
                    logging.warning(f"Error processing row {i} in sheet {sheet_name}: {e}")

        except Exception as e:
            logging.error(f"Error syncing sheet {sheet_name}: {e}")

    def update_product_quantity(self, product: Product, new_quantity: int) -> bool:
        """Update product quantity in Google Sheets and database"""
        try:
            if product.sheet_name not in self.product_sheets:
                return False

            worksheet = self.product_sheets[product.sheet_name]

            worksheet.update_cell(product.sheet_row, CONFIG.COL_QUANTITY + 1, new_quantity)
            product.quantity = new_quantity
            self.product_repo.update(product)
            return True
        except Exception as e:
            logging.error(f"Error updating product quantity: {e}")
            return False

    async def start_periodic_refresh(self, interval_seconds=15):
        """Start periodic refresh task"""
        self.periodic_refresh_task = asyncio.create_task(self.periodic_refresh(interval_seconds))

    async def stop_periodic_refresh(self):
        """Stop periodic refresh task"""
        if self.periodic_refresh_task:
            self.periodic_refresh_task.cancel()
            self.periodic_refresh_task = None

    async def periodic_refresh(self, interval_seconds):
        """Periodically refresh data from Google Sheets"""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                self.sync_products()
            except Exception as e:
                logging.error(f"Error during periodic refresh: {e}")
