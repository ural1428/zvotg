import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Бот запущен 🚀")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
