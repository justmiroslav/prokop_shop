import gspread, logging, asyncio, time
from google.auth.exceptions import RefreshError
from gspread.exceptions import APIError
from sqlalchemy.orm import Session
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from typing import Set, Callable, Any

from utils.config import CONFIG, get_credentials
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
        self.sheet = None
        self.product_sheets = {}

        self.update_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.sync_task = None
        self.queue_task = None

        self._init_sheets()

    def _init_sheets(self):
        """Initialize Google Sheets client and worksheets"""
        self.sheet = self.client.open_by_key(CONFIG.SHEET_ID)
        self.product_sheets = {sheet.title: sheet for sheet in self.sheet.worksheets() if sheet.title != CONFIG.EXCLUDED_SHEET}

        for sheet_name, worksheet in self.product_sheets.items():
            header = worksheet.row_values(1)
            CONFIG.PRODUCT_CATEGORIES[sheet_name] = header[CONFIG.COL_ATTRIBUTE]

    @staticmethod
    def get_client() -> gspread.Client:
        """Get Google Sheets client"""
        return gspread.service_account_from_dict(info=get_credentials(), scopes=CONFIG.SCOPES)

    def retry_with_backoff(self, func: Callable, *args, max_retries: int = 3, **kwargs) -> Any:
        """Execute function with exponential backoff retry on auth errors"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (RefreshError, APIError):
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    self.client = self.get_client()
                    self._init_sheets()
                else:
                    logging.error("Max retries reached in retry_with_backoff")
            except Exception as e:
                logging.error(f"Unexpected error in retry_with_backoff: {e}")
        return None

    async def sync_products(self):
        """Async product sync with sequential sheet processing for DB safety"""
        try:
            loop = asyncio.get_event_loop()
            for sheet_name, worksheet in self.product_sheets.items():
                await loop.run_in_executor(self.executor, self._sync_sheet_products, sheet_name, worksheet)
        except Exception as e:
            logging.error(f"Error in sync_products: {e}")

    def _sync_sheet_products(self, sheet_name: str, worksheet: gspread.Worksheet):
        """Sync products from specific worksheet"""
        try:
            data = self.retry_with_backoff(worksheet.get_all_values)
            if len(data) <= 1:
                return

            sheet_products: Set[tuple] = set()

            for i, row in enumerate(data[1:], start=2):
                if len(row) < CONFIG.COL_COST + 1:
                    continue

                try:
                    name, attribute = row[CONFIG.COL_PRODUCT], row[CONFIG.COL_ATTRIBUTE]
                    if not name or not attribute:
                        continue

                    quantity, price, cost = int(row[CONFIG.COL_QUANTITY]), float(row[CONFIG.COL_PRICE]), float(row[CONFIG.COL_COST])
                    sheet_products.add((name, attribute))
                    product = self.product_repo.get_by_name_attribute(sheet_name, name, attribute)

                    if product:
                        if product.is_archived:
                            self.product_repo.unarchive_product(product)

                        needs_update = (product.quantity != quantity or product.price != price or
                            product.cost != cost or product.sheet_row != i)

                        if needs_update:
                            product.name, product.attribute, product.quantity = name, attribute, quantity
                            product.price, product.cost, product.sheet_row = price, cost, i
                            self.product_repo.update(product)
                    else:
                        product = Product(sheet_name=sheet_name, sheet_row=i, name=name,
                                          attribute=attribute, quantity=quantity, price=price, cost=cost)
                        self.product_repo.create(product)

                except (ValueError, IndexError) as e:
                    logging.warning(f"Row {i} in {sheet_name}: {e}")

            for product in self.product_repo.get_all_by_sheet(sheet_name):
                if (product.name, product.attribute) not in sheet_products:
                    self.product_repo.archive_product(product)

        except Exception as e:
            logging.error(f"Error syncing {sheet_name}: {e}")

    def queue_quantity_update(self, product: Product, new_quantity: int) -> bool:
        try:
            product.quantity = new_quantity
            self.product_repo.update(product)
            logging.info(f"Queued update for product {product.full_name}")

            update = QuantityUpdate(product.id, new_quantity, product.sheet_name, product.sheet_row)

            try:
                self.update_queue.put_nowait(update)
                return True
            except asyncio.QueueFull:
                logging.warning("Update queue full, skipping sheet update")
                return True

        except Exception as e:
            logging.error(f"Error queuing update: {e}")
            return False

    async def _process_update_queue(self):
        """Process sheet updates from queue"""
        while True:
            try:
                update = await self.update_queue.get()
                await self._process_single_update(update)
                self.update_queue.task_done()
            except Exception as e:
                logging.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)

    async def _process_single_update(self, update: QuantityUpdate):
        """Process single sheet update"""
        try:
            logging.info(f"Processing update for product {update.product_id}: {update.new_quantity} in {update.sheet_name}")
            if update.sheet_name not in self.product_sheets:
                return

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._update_sheet_quantity,
                update.sheet_name, update.sheet_row, update.new_quantity
            )
        except Exception as e:
            logging.error(f"Sheet update error for product {update.product_id}: {e}")

    def _update_sheet_quantity(self, sheet_name: str, row: int, quantity: int):
        """Update quantity in sheet"""
        logging.info(f"Updating {sheet_name} row {row} quantity to {quantity}")
        worksheet = self.product_sheets[sheet_name]
        self.retry_with_backoff(worksheet.update_cell, row, CONFIG.COL_QUANTITY + 1, quantity)

    async def start_background_tasks(self, refresh_interval=15):
        """Start background tasks with initial delay"""
        self.queue_task = asyncio.create_task(self._process_update_queue())
        self.sync_task = asyncio.create_task(self._periodic_sync(refresh_interval))

    async def stop_background_tasks(self):
        """Stop background tasks and cleanup"""
        for task in [self.queue_task, self.sync_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self.update_queue.join()
        self.executor.shutdown(wait=True)

    async def _periodic_sync(self, interval_seconds):
        """Periodic sync with initial delay"""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                await self.sync_products()
            except Exception as e:
                logging.error(f"Periodic sync error: {e}")
