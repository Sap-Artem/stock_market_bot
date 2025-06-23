from aiogram import Router, types
from aiogram.types import Message
from database.queries.users import user_exists
from aiogram.filters import Command
from keyboards.inline import get_main_menu


router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    if user_exists(message.from_user.id):
        await message.answer("Вы уже зарегистрированы. Добро пожаловать в трейдинг-бот!", reply_markup=get_main_menu())
    else:
        await message.answer("Привет! Добро пожаловать. Пожалуйста, отправьте команду /register, чтобы зарегистрироваться.")
