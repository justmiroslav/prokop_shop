from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from utils.keyboards import get_adjustment_keyboard, get_all_adjustments_keyboard, get_order_actions_keyboard
from utils.states import OrderStates
from utils.shit_utils import format_order_msg
from service.order_service import OrderService

router = Router()

@router.callback_query(F.data.startswith("profit_adj:"))
async def select_profit_adjustment_type(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Handle profit adjustment type selection"""
    adj_type = callback.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("order_id")

    order = order_service.get_order(order_id)
    order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
    text = "прибавить к профиту" if adj_type == "add" else "вычесть из профита"

    await callback.message.edit_text(order_text + f"\n\nВведи сумму, которую нужно {text}")
    await state.update_data(adj_type=adj_type)
    await state.set_state(OrderStates.ENTER_ADJUSTMENT_AMOUNT)
    await callback.answer()

@router.message(OrderStates.ENTER_ADJUSTMENT_AMOUNT)
async def handle_adjustment_amount(message: Message, state: FSMContext, order_service: OrderService):
    """Handle entering adjustment amount"""
    try:
        amount_text = message.text.replace(",", ".").strip()
        amount = float(amount_text)

        data = await state.get_data()
        adj_type = data.get("adj_type")
        amount = abs(amount) if adj_type == "add" else -abs(amount)

        await state.update_data(adj_amount=amount)
        await state.set_state(OrderStates.ENTER_ADJUSTMENT_REASON)

        await message.answer("Введи причину корректировки")
    except ValueError:
        data = await state.get_data()
        order_id, adj_type = data.get("order_id"), data.get("adj_type")

        order = order_service.get_order(order_id)
        order_text = f"Заказ {order.id}\n\n" + format_order_msg(order)
        text = "прибавить к профиту" if adj_type == "add" else "вычесть из профита"

        await message.edit_text(order_text + f"\n\nВведи корректное число которое нужно {text}\n\nНапример, 100 или 100.50")

@router.message(OrderStates.ENTER_ADJUSTMENT_REASON)
async def handle_adjustment_reason(message: Message, state: FSMContext, order_service: OrderService):
    """Handle entering adjustment reason"""
    reason = message.text.strip()

    if not reason:
        await message.edit_text("Причина не может быть пустой\n\nВведи ещё раз")
        return

    data = await state.get_data()
    order_id, amount = data.get("order_id"), data.get("adj_amount")
    order = order_service.get_order(order_id)

    success, result_message = order_service.add_profit_adjustment(order, amount, reason)
    if not success:
        await message.answer(f"Ошибка: {result_message}", reply_markup=get_order_actions_keyboard())
        return

    upd_order = order_service.get_order(order_id)
    order_text = f"Заказ {upd_order.id}\n\n" + format_order_msg(upd_order)
    await message.answer(f"✅ Корректировка добавлена!\n\n{order_text}", reply_markup=get_order_actions_keyboard())
    await state.clear()
    await state.update_data(context="orders", order_id=order_id, action="edit")

@router.callback_query(F.data == "add_adj")
async def add_new_adjustment(callback: CallbackQuery):
    """Start adding a new profit adjustment"""
    await callback.message.edit_text("Выбери тип корректировки профита",
        reply_markup=get_adjustment_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_adj:"))
async def delete_adjustment(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Delete a profit adjustment"""
    adj_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    order_id = data.get("order_id")

    success, message = order_service.delete_profit_adjustment(adj_id)
    if not success:
        await callback.message.edit_text(f"Ошибка: {message}", reply_markup=get_order_actions_keyboard())
        await callback.answer()
        return

    adjustments = order_service.get_profit_adjustments(order_id)
    if adjustments:
        await callback.message.edit_text(f"Корректировка удалена\n\nОставшиеся корректировки профита",
            reply_markup=get_all_adjustments_keyboard(adjustments)
        )
    else:
        await callback.message.edit_text("Все корректировки удалены. Выбери тип новой корректировки профита",
            reply_markup=get_adjustment_keyboard()
        )

    await callback.answer()
