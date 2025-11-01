from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio

from aiogram.types import BotCommand

from config import API_TOKEN
from admin_panel import router as admin_router
from uchaskavoy_panel import router as uchaskavoy_router
from fuqarolik_panel import router as fuqarolik_router  # 🔥 Qo‘shilgan
from database import create_tables


async def main():
    create_tables()

    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # 🔽 Routerlarni tartib bilan qo‘shamiz
    dp.include_router(admin_router)
    dp.include_router(uchaskavoy_router)
    dp.include_router(fuqarolik_router)  # 🔥 Muhim

    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Asosiy menyu"),
        # BotCommand(command="help", description="ℹ️ Yordam olish")
    ])

    print("🤖 Bot ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
