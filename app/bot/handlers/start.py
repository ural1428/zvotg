from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database.session import AsyncSessionLocal
from app.services.user_service import get_or_create_user
from app.bot.keyboards.main_menu import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):

    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, message.from_user)

    text = (
        "👋 Добро пожаловать в VPN сервис\n\n"
        "🔐 Быстрое и безопасное подключение\n"
        "🌍 Работает на всех устройствах\n\n"
        "Выберите действие:"
    )

    await message.answer(
        text,
        reply_markup=main_menu_keyboard
    )
