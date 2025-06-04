import gspread, logging, asyncio
from google.oauth2.service_account import Credentials
from sqlalchemy.orm import Session
from dataclasses import dataclass

from utils.config import CONFIG
from database.models import Product
from repository.product_repository import ProductRepository

@dataclass
class QuantityUpdate:
    product_id: int
    new_quantity: int
    sheet_name: str
    sheet_row: int

class SheetManager:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.product_repo = ProductRepository(db_session)
        self.client = self.get_client()
        self.sheet = self.client.open_by_key(CONFIG.SHEET_ID)
        self.product_sheets = {sheet.title: sheet for sheet in self.sheet.worksheets() if
                               sheet.title != CONFIG.EXCLUDED_SHEET}

        self.update_queue = asyncio.Queue()
        self.lock = asyncio.Semaphore(1)
        self.periodic_refresh_task = None
        self.queue_worker_task = None

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

                    product = self.product_repo.get_by_name_attribute(sheet_name, name, attribute)

                    if product:
                        if product.quantity != quantity or product.price != price or product.cost != cost:
                            product.name = name
                            product.attribute = attribute
                            product.quantity = quantity
                            product.price = price
                            product.cost = cost
                            self.product_repo.update(product)
                    else:
                        product = Product(sheet_name=sheet_name, sheet_row=i,
                                          name=name, attribute=attribute, quantity=quantity,
                                          price=price, cost=cost
                                          )
                        self.product_repo.create(product)

                except (ValueError, IndexError) as e:
                    logging.warning(f"Error processing row {i} in sheet {sheet_name}: {e}")

        except Exception as e:
            logging.error(f"Error syncing sheet {sheet_name}: {e}")

    def queue_quantity_update(self, product: Product, new_quantity: int) -> bool:
        try:
            product.quantity = new_quantity
            self.product_repo.update(product)

            update = QuantityUpdate(
                product_id=product.id,
                new_quantity=new_quantity,
                sheet_name=product.sheet_name,
                sheet_row=product.sheet_row
            )

            try:
                self.update_queue.put_nowait(update)
                return True
            except asyncio.QueueFull:
                logging.warning("Update queue is full, skipping sheet update")
                return True

        except Exception as e:
            logging.error(f"Error queuing product update: {e}")
            return False

    async def _process_update_queue(self):
        while True:
            try:
                update = await self.update_queue.get()
                async with self.lock:
                    await self._process_single_update(update)
                self.update_queue.task_done()
            except Exception as e:
                logging.error(f"Error processing update queue: {e}")
                await asyncio.sleep(1)

    async def _process_single_update(self, update: QuantityUpdate):
        try:
            if update.sheet_name not in self.product_sheets:
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._update_sheet_quantity,
                update.sheet_name,
                update.sheet_row,
                update.new_quantity
            )
        except Exception as e:
            logging.error(f"Error updating sheet for product {update.product_id}: {e}")

    def _update_sheet_quantity(self, sheet_name: str, row: int, quantity: int):
        worksheet = self.product_sheets[sheet_name]
        worksheet.update_cell(row, CONFIG.COL_QUANTITY + 1, quantity)

    async def start_background_tasks(self, refresh_interval=15):
        self.queue_worker_task = asyncio.create_task(self._process_update_queue())
        self.periodic_refresh_task = asyncio.create_task(self._periodic_refresh(refresh_interval))

    async def stop_background_tasks(self):
        if self.queue_worker_task:
            self.queue_worker_task.cancel()
            try:
                await self.queue_worker_task
            except asyncio.CancelledError:
                pass

        if self.periodic_refresh_task:
            self.periodic_refresh_task.cancel()
            try:
                await self.periodic_refresh_task
            except asyncio.CancelledError:
                pass

        await self.update_queue.join()

    async def _periodic_refresh(self, interval_seconds):
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                async with self.lock:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.sync_products)
            except Exception as e:
                logging.error(f"Error during periodic refresh: {e}")
