from aiogram.fsm.state import StatesGroup, State

class ProductStates(StatesGroup):
    """States for the product operations"""
    CATEGORY = State()
    PRODUCT = State()
    ATTRIBUTE = State()
    QUANTITY = State()

class SaleStates(StatesGroup):
    """States for the sale statistics"""
    SELECT_PERIOD = State()
    CATEGORY = State()
