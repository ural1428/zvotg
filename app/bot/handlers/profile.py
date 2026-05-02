from aiogram import Router, F
from aiogram.types import Message

from app.database.session import AsyncSessionLocal
from app.services.subscription_service import (
    get_latest_subscription,
    get_subscription_days_left,
    is_subscription_active,
)

router = Router()


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    async with AsyncSessionLocal() as session:
        subscription = await get_latest_subscription(
            session=session,
            telegram_id=message.from_user.id,
        )

    is_active = is_subscription_active(subscription)
    days_left = get_subscription_days_left(subscription)

    if is_active:
        status_text = "✅ Активна"
        days_text = f"{days_left} дн."
    else:
        status_text = "❌ Не активна"
        days_text = "0 дн."

    await message.answer(
        "👤 Ваш профиль\n\n"
        f"ID: `{message.from_user.id}`\n"
        f"Подписка: {status_text}\n"
        f"Осталось: {days_text}",
        parse_mode="Markdown",
    )
