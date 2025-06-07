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
    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)
    text = "прибавить к профиту" if adj_type == "add" else "вычесть из профита"

    await callback.message.edit_text(order_text + f"\nВведи сумму, которую нужно {text}")
    await state.update_data(adj_type=adj_type, prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id
    )
    await state.set_state(OrderStates.ENTER_ADJUSTMENT_AMOUNT)
    await callback.answer()

@router.message(OrderStates.ENTER_ADJUSTMENT_AMOUNT)
async def handle_adjustment_amount(message: Message, state: FSMContext, order_service: OrderService):
    """Handle entering adjustment amount"""
    data = await state.get_data()
    order_id, adj_type = data.get("order_id"), data.get("adj_type")
    prompt_chat_id, prompt_message_id = data.get("prompt_chat_id"), data.get("prompt_message_id")
    order = order_service.get_order(data.get("order_id"))
    text = "прибавить к профиту" if adj_type == "add" else "вычесть из профита"
    order_text = f"Заказ {order.display_name}\n" + format_order_msg(order)

    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            await message.bot.edit_message_text(chat_id=prompt_chat_id, message_id=prompt_message_id,
                text=f"{order_text}\nМожно {text} только положительное число\nВведи корректное число")
            return

        amount = amount if adj_type == "add" else -amount
        await state.update_data(adj_amount=amount)
        await state.set_state(OrderStates.ENTER_ADJUSTMENT_REASON)
        await message.answer("Введи причину корректировки")
    except (ValueError, TypeError):
        await message.bot.edit_message_text(chat_id=prompt_chat_id, message_id=prompt_message_id,
            text=f"{order_text}\nВведи число а не строку"
        )

@router.message(OrderStates.ENTER_ADJUSTMENT_REASON)
async def handle_adjustment_reason(message: Message, state: FSMContext, order_service: OrderService):
    """Handle entering adjustment reason"""
    reason = message.text.strip()
    data = await state.get_data()
    order_id, amount = data.get("order_id"), data.get("adj_amount")
    order = order_service.get_order(order_id)

    order_service.add_profit_adjustment(order, amount, reason)

    upd_order = order_service.get_order(order_id)
    order_text = f"Заказ {upd_order.display_name}\n" + format_order_msg(upd_order)
    response = await message.answer(order_text, reply_markup=get_order_actions_keyboard())
    await state.clear()
    await state.update_data(context="orders", order_id=order_id, action="view_edit", inline_message_id=response.message_id)

@router.callback_query(F.data == "add_adj")
async def add_new_adjustment(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Start adding a new profit adjustment"""
    data = await state.get_data()
    order_id = data.get("order_id")
    order = order_service.get_order(order_id)
    await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери тип корректировки профита",
        reply_markup=get_adjustment_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_adj:"))
async def delete_adjustment(callback: CallbackQuery, state: FSMContext, order_service: OrderService):
    """Delete a profit adjustment"""
    adj_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    order_id = data.get("order_id")

    order_service.delete_profit_adjustment(adj_id)

    order = order_service.get_order(order_id)
    adjustments = order_service.get_profit_adjustments(order_id)
    if adjustments:
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nСуществующие корректировки профита",
            reply_markup=get_all_adjustments_keyboard(adjustments)
        )
    else:
        await callback.message.edit_text(f"Заказ {order.display_name}\n\nВыбери тип корректировки профита",
            reply_markup=get_adjustment_keyboard()
        )

    await callback.answer()
