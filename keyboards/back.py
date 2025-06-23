from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def go_back_keyboard(asset_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"asset_{asset_id}")]
    ])