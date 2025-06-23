from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

request_phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton(text="💼 Мой портфель", callback_data="portfolio")],
        [InlineKeyboardButton(text="📃 Список активов", callback_data="assets")],
        [InlineKeyboardButton(text="📝 Мои заявки", callback_data="requests")],
        [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def my_orders_keyboard(include_completed=True):
    buttons = []
    if include_completed:
        buttons.append(
            [InlineKeyboardButton(text="📄 Исполненные заявки", callback_data="view_completed_orders")]
        )
    buttons.append(
        [InlineKeyboardButton(text="❌ Отмена заявок", callback_data="cancel_orders_menu")]
    )
    buttons.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_portfolio_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main_menu")]
        ]
    )
def get_assets_keyboard(assets: list):
    keyboard = [
        [InlineKeyboardButton(text=a[1], callback_data=f"asset_{a[0]}")]
        for a in assets
    ]
    keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_asset_action_keyboard(asset_id, in_portfolio=False):
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{asset_id}")]
    ]
    if in_portfolio:
        buttons.append([InlineKeyboardButton(text="💼 Продать", callback_data=f"sell_{asset_id}")])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="assets")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_order_type_keyboard(asset_id, action: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Рыночная", callback_data=f"{action}_market_{asset_id}"),
            InlineKeyboardButton(text="📈 Лимитная", callback_data=f"{action}_limit_{asset_id}")
        ],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"asset_{asset_id}")]
    ])
