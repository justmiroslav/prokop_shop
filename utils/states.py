from aiogram.fsm.state import StatesGroup, State

class AuthStates(StatesGroup):
    """States for authentication"""
    WAITING_FOR_PASSWORD = State()

class OrderStates(StatesGroup):
    """States for order operations"""
    SELECT_QUANTITY = State()
    EDIT_QUANTITY = State()
    ENTER_ADJUSTMENT_AMOUNT = State()
    ENTER_ADJUSTMENT_REASON = State()

class StatisticsStates(StatesGroup):
    """States for the sale statistics"""
    SELECT_PERIOD = State()
