from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_connection
from keyboards.back import go_back_keyboard
from keyboards.inline import get_order_type_keyboard, get_assets_keyboard
from database.queries.orders import create_order, try_execute_order, cancel_order
from database.queries.assets import get_asset_by_id

router = Router()

class OrderFSM(StatesGroup):
    waiting_for_limit_price = State()
    waiting_for_quantity = State()
    waiting_for_market_confirmation = State()

user_order_context = {}

@router.callback_query(F.data.regexp(r"^(buy|sell)_[0-9]+$"))
async def handle_buy_sell(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    parts = callback.data.split("_")
    action = parts[0]
    asset_id = int(parts[1])

    user_order_context[callback.from_user.id] = {"action": action, "asset_id": asset_id}
    await callback.message.edit_text(
        f"Выберите тип заявки:",
        reply_markup=get_order_type_keyboard(asset_id, action)
    )

@router.callback_query(F.data.regexp(r"^(buy|sell)_market_[0-9]+$"))
async def handle_market_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    parts = callback.data.split("_")
    action = parts[0]
    asset_id = int(parts[2])

    asset = get_asset_by_id(asset_id)
    user_order_context[callback.from_user.id] = {
        "action": action,
        "asset_id": asset_id,
        "order_type": "market",
        "price": asset[1]
    }

    await state.set_state(OrderFSM.waiting_for_quantity)
    await callback.message.edit_text(
        f"Текущая цена {asset[0]}: {asset[1]:.2f} ₽\nВведите количество лотов для {('покупки' if action == 'buy' else 'продажи')}:"
    )

@router.callback_query(F.data.regexp(r"^(buy|sell)_limit_[0-9]+$"))
async def handle_limit_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    parts = callback.data.split("_")
    action = parts[0]
    asset_id = int(parts[2])

    user_order_context[callback.from_user.id] = {
        "action": action,
        "asset_id": asset_id,
        "order_type": "limit"
    }

    await state.set_state(OrderFSM.waiting_for_limit_price)
    await callback.message.edit_text("Введите желаемую цену заявки (в ₽):")

@router.message(OrderFSM.waiting_for_limit_price)
async def handle_limit_price_input(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
        user_order_context[message.from_user.id]["price"] = price
        await state.set_state(OrderFSM.waiting_for_quantity)
        await message.answer("Введите количество лотов:")
    except ValueError:
        await message.answer("Введите корректное число (пример: 245.00)")

@router.callback_query(F.data.regexp(r"^cancel_order_[0-9]+$"))
async def cancel_order_handler(callback: CallbackQuery):
    await callback.answer()
    order_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    cancel_order(order_id, user_id)
    await callback.message.edit_text("Заявка успешно отменена ✅")

def get_internal_user_id(telegram_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id_users FROM users WHERE telegram_id = %s", (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    else:
        raise ValueError(f"Пользователь с telegram_id={telegram_id} не найден.")

@router.message(OrderFSM.waiting_for_quantity)
async def handle_market_order_quantity_input(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        user_id = get_internal_user_id(telegram_id)
    except ValueError as e:
        await message.answer("Не удалось найти пользователя. Попробуйте позже.")
        await state.clear()
        return

    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное количество (целое число больше 0):")
        return

    ctx = user_order_context.get(telegram_id)
    if not ctx:
        await message.answer("Что-то пошло не так. Попробуйте сначала.")
        await state.clear()
        return

    asset_id = ctx["asset_id"]
    action = ctx["action"]
    order_type = ctx["order_type"]
    price = ctx["price"]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT quantity_of_assets_in_lots FROM assets WHERE id_assets = %s", (asset_id,))
    lot_size = cur.fetchone()[0]
    cur.close()
    conn.close()

    actual_quantity = quantity * lot_size

    success = create_order(
        user_id=user_id,
        asset_id=asset_id,
        price=price,
        quantity=actual_quantity,
        direction=action,
        order_type=order_type,
    )

    if success == "insufficient_funds":
        await message.answer(
            "❌ <b>Денежных средств недостаточно.</b>\n"
            "Пополните счёт или измените количество лотов.",
            reply_markup=go_back_keyboard(asset_id),
            parse_mode="HTML"
        )
        await state.clear()
        return

    if success == "insufficient_assets":
        await message.answer(
            "❌ <b>У вас недостаточное количество актива.</b>\n"
            "Уменьшите количество лотов, чтобы продолжить.",
            reply_markup=go_back_keyboard(asset_id),
            parse_mode="HTML"
        )
        await state.clear()
        return

    try_execute_order(
        telegram_id=telegram_id,
        asset_id=asset_id,
        quantity=actual_quantity,
        price=price,
        direction=action,
        order_type=order_type
    )

    await message.answer(
        f"{'Рыночная' if order_type == 'market' else 'Лимитная'} заявка на {action} {quantity} лотов по цене {price:.2f} ₽ отправлена.",
        reply_markup=go_back_keyboard(asset_id)
    )
    await state.clear()
