from aiogram.fsm.state import StatesGroup, State

class AuthStates(StatesGroup):
    WAITING_FOR_PASSWORD = State()

class ProductStates(StatesGroup):
    """States for the product operations"""
    ORDER_ID = State()

class SaleStates(StatesGroup):
    """States for the sale statistics"""
    SELECT_PERIOD = State()
