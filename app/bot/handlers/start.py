from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.database.session import AsyncSessionLocal
from app.services.referral_service import (
    create_referral_if_allowed,
    parse_referral_code,
)
from app.services.user_service import get_or_create_user

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)

        referrer_telegram_id = parse_referral_code(command.args)

        if referrer_telegram_id:
            await create_referral_if_allowed(
                session=session,
                referrer_telegram_id=referrer_telegram_id,
                referred_telegram_id=user.telegram_id,
            )

    text = (
        "👋 Добро пожаловать!\n\n\n"
        " ZVOtg это VPN на технологии IKEv2:\n\n"
        "💎 IKEv2 — самый быстрый, стабильный и безопасный VPN-протокол\n"
        "📱 Работает на всех устройствах\n"
        "🇷🇺 Мы говорим на вашем языке\n"
        "💬 Круглосуточная тех. поддержка\n\n"
        "👇🏼 Выберите действие:"
    )

    await message.answer(
        text,
        reply_markup=main_menu_keyboard,
    )