from aiogram.fsm.state import StatesGroup, State

class AuthStates(StatesGroup):
    """States for authentication"""
    WAITING_FOR_PASSWORD = State()

class OrderStates(StatesGroup):
    """States for order operations"""
    EDIT_QUANTITY = State()

class StatisticsStates(StatesGroup):
    """States for the sale statistics"""
    SELECT_PERIOD = State()
