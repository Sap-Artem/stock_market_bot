import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start, register, menu, orders_type, assets, cancel_orders


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_routers(start.router, register.router, menu.router)
    dp.include_router(orders_type.router)
    dp.include_router(assets.router)
    dp.include_router(cancel_orders.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
