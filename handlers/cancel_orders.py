from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.queries.orders import get_active_orders_by_telegram_id, cancel_order_by_id, get_order_by_id
from database.queries.assets import get_asset_name_by_id
from keyboards.back import go_back_keyboard

router = Router()

@router.message(F.text == "Отмена заявок")
async def cancel_orders_message(message: Message):
    await cancel_orders_menu(
        user_id=message.from_user.id,
        send_func=lambda *args, **kwargs: message.answer(*args, **kwargs)
    )

async def cancel_orders_menu(user_id: int, send_func):
    orders = get_active_orders_by_telegram_id(user_id)

    if not orders:
        await send_func("У вас нет активных заявок.")
        return

    buttons = []
    for order in orders:
        order_id, direction, asset_id = order["id_orders"], order["direction"], order["id_assets"]
        asset_name = get_asset_name_by_id(asset_id)
        button_text = f"{order_id} - {direction} - {asset_name}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"cancel_order:{order_id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("Выберите заявку для отмены:", reply_markup=markup)


@router.callback_query(F.data.startswith("cancel_order:"))
async def process_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])

    order = get_order_by_id(order_id)
    asset_id = order["id_assets"] if order else None

    success = cancel_order_by_id(order_id)

    text = (
        f"Заявка #{order_id} успешно отменена ❌"
        if success else
        f"Не удалось отменить заявку #{order_id} (возможно, она уже исполнена)."
    )

    markup = go_back_keyboard(asset_id) if asset_id else None
    await callback.message.edit_text(text, reply_markup=markup)

    await callback.answer()

@router.callback_query(F.data == "cancel_orders_menu")
async def cancel_orders_callback(callback: CallbackQuery):
    try:
        await cancel_orders_menu(
            user_id=callback.from_user.id,
            send_func=lambda *args, **kwargs: callback.message.edit_text(*args, **kwargs)
        )
    except Exception as e:
        print("Ошибка в cancel_orders_callback:", e)
    finally:
        await callback.answer()