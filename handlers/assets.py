from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from database.queries.assets import get_asset_by_id, get_asset_order_book
from database.queries.balance import get_user_balance
from database.queries.portfolio import get_user_portfolio_by_telegram_id
from keyboards.inline import get_asset_action_keyboard

router = Router()

@router.callback_query(F.data.startswith("asset_"))
async def handle_asset_details(callback: CallbackQuery):
    await callback.answer()
    asset_id = int(callback.data.split("_")[1])
    asset = get_asset_by_id(asset_id)
    order_book = get_asset_order_book(asset_id)
    portfolio = get_user_portfolio_by_telegram_id(callback.from_user.id)

    in_portfolio = any(a[0] == asset[0] for a in portfolio)
    telegram_id = callback.from_user.id
    balance = get_user_balance(telegram_id)

    text = f"📈 <b>{asset[0]}</b>\n💵 Текущая цена: {asset[1]:.2f} ₽\n\n💰 Баланс: {balance:.2f} ₽\n\n📊 <b>Стакан:</b>\n"

    if order_book:
        for price, volume, direction in order_book:
            if volume != 0:
                emoji = "🔼" if direction == "buy" else "🔽"
                text += f"{emoji} {direction.title()} | {volume} @ {price:.2f} ₽\n"
    else:
        text += "Нет заявок на данный момент."

    await callback.message.edit_text(
        text, reply_markup=get_asset_action_keyboard(asset_id, in_portfolio),
        parse_mode="HTML"
    )
