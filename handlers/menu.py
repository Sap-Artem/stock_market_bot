from aiogram import Router, F, types
from aiogram.types import CallbackQuery

from database.queries.balance import get_user_balance
from database.queries.orders import get_active_orders_by_user, get_completed_orders_by_user
from database.queries.portfolio import get_user_portfolio_by_telegram_id
from keyboards.inline import get_main_menu, my_orders_keyboard, get_portfolio_keyboard
from database.queries.assets import get_all_assets, get_asset_by_id, get_asset_order_book
from keyboards.inline import get_assets_keyboard, get_asset_action_keyboard


router = Router()

def format_order_entry(order):
    return (
        f"🆔 Заявка #{order[0]}\n"
        f"📈 Актив: {order[8]}\n"
        f"🔢 Кол-во: {order[1]} (исполнено: {order[2]})\n"
        f"💰 Цена: {order[3]:.2f}\n"
        f"📌 Тип: {order[4]} ({order[5]})\n"
        f"📅 Дата: {order[7].strftime('%d.%m.%Y')}\n"
        f"⚙ Статус: {order[6]}\n\n"
    )

@router.callback_query(F.data == "portfolio")
async def handle_portfolio(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    telegram_id = callback.from_user.id
    balance = get_user_balance(telegram_id)
    portfolio = get_user_portfolio_by_telegram_id(user_id)

    if not portfolio:
        await callback.message.answer("📭 У вас пока нет активов в портфеле.")
        return

    total_pl = 0
    text = "💼 Ваш портфель: \n\n"
    text += f"💰 Баланс: {balance:.2f} ₽ \n\n"

    for asset_name, current_price, qty, buy_price in portfolio:
        delta = (current_price - buy_price) * qty
        percent = ((current_price / buy_price) - 1) * 100 if buy_price != 0 else 0
        sign = "🔺" if delta > 0 else "🔻" if delta < 0 else "⏺"

        text += (
            f"• {asset_name}\n"
            f"  Кол-во: {qty} акций\n"
            f"  Покупка: {buy_price:.2f} ₽ → Текущая: {current_price:.2f} ₽\n"
            f"  Доходность: {sign} {delta:+.2f} ₽ ({percent:+.2f}%)\n\n"
        )
        total_pl += delta

    final_sign = "🔺" if total_pl > 0 else "🔻" if total_pl < 0 else "⏺"
    text += f"📊 Общий P&L: {final_sign} {total_pl:+.2f} ₽"

    await callback.message.answer(text, reply_markup=get_portfolio_keyboard())

@router.callback_query(F.data == "back_to_main_menu")
async def handle_back_to_main_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("📋 Главное меню:", reply_markup=get_main_menu())

@router.callback_query(F.data == "requests")
async def handle_requests(callback: CallbackQuery):
    await callback.answer()
    print("Нажата кнопка 'Мои заявки'")
    user_id = callback.from_user.id
    orders = get_active_orders_by_user(user_id)

    text = "🕐 У вас нет активных заявок." if not orders else (
        "📄 Ваши активные заявки:\n\n" + "".join([format_order_entry(o) for o in orders])
    )
    await callback.message.edit_text(text, reply_markup=my_orders_keyboard())

@router.callback_query(F.data == "view_completed_orders")
async def handle_completed_orders(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    try:
        orders = get_completed_orders_by_user(user_id)
        if not orders:
            await callback.message.edit_text("📭 У вас пока нет исполненных заявок.", reply_markup=my_orders_keyboard())
            return

        text = "📄 Ваши исполненные заявки:\n\n" + "".join([format_order_entry(o) for o in orders])
        await callback.message.edit_text(text, reply_markup=my_orders_keyboard(include_completed=False))
    except Exception as e:
        await callback.message.answer("❌ Произошла ошибка при получении заявок.")
        print(f"Ошибка при обработке исполненных заявок: {e}")

@router.callback_query(F.data == "info")
async def handle_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("ℹ️ Это финансовый бот. Версия: 1.0.0")

@router.callback_query(F.data == "assets")
async def handle_assets(callback: CallbackQuery):
    await callback.answer()
    assets = get_all_assets()
    await callback.message.edit_text("📃 Выберите актив:", reply_markup=get_assets_keyboard(assets))