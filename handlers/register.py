from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import request_phone_kb
from database.queries.users import insert_user
from keyboards.inline import get_main_menu

router = Router()

class RegisterStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()


@router.message(F.text.lower() == "/register")
async def cmd_register(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RegisterStates.waiting_for_name)
    await message.answer("Введите ваше имя:")


@router.message(RegisterStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Теперь нажмите кнопку, чтобы отправить номер телефона:",
        reply_markup=request_phone_kb
    )
    await state.set_state(RegisterStates.waiting_for_phone)


@router.message(RegisterStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Пожалуйста, нажмите кнопку ниже, чтобы отправить номер телефона.")
        return
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("Введите ваш email:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RegisterStates.waiting_for_email)


@router.message(RegisterStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)

    data = await state.get_data()
    insert_user(
        telegram_id=message.from_user.id,
        name=data['name'],
        phone=data['phone'],
        email=data['email']
    )

    await message.answer("Регистрация завершена ✅", reply_markup=get_main_menu())
    await state.clear()

