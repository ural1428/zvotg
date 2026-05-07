import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv
import os

load_dotenv()

bot = Bot(token=os.getenv("SUPPORT_BOT_TOKEN"))
dp = Dispatcher()


@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def show_chat_id(message: Message):
    print("CHAT ID:", message.chat.id)
    print("CHAT TITLE:", message.chat.title)
    await message.answer(f"Chat ID: `{message.chat.id}`", parse_mode="Markdown")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
