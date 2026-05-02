from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from app.config import config
from app.database.models import User
from app.database.session import AsyncSessionLocal
from app.integrations.mikrotik.manager import MikroTikManager
from app.services.subscription_service import (
    create_new_pending_subscription,
    get_user_subscriptions,
    mark_cert_created,
    grant_subscription_until_2100,
    send_certificate,
)

router = Router()


def cert_file_exists(cert_path: str | None) -> bool:
    if not cert_path:
        return False

    return Path(cert_path).exists()


@router.message(F.text)
async def easter_egg_handler(message: Message):
    if not config.easter_egg_code:
        return

    if message.text.strip() != config.easter_egg_code:
        return

    telegram_id = message.from_user.id

    await message.answer("👑 Секретный код принят. Активирую золотую подписку...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("Сначала нажмите /start.")
            return

        subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=telegram_id,
        )

        if subscriptions:
            subscription = subscriptions[0]
        else:
            subscription = await create_new_pending_subscription(
                session=session,
                user_id=user.id,
                telegram_id=telegram_id,
            )

        if not cert_file_exists(subscription.cert_path):
            await message.answer("⏳ Создаю VPN-сертификат...")

            manager = MikroTikManager(config.mikrotik)

            cert_path = await manager.certs.create_cert(subscription.cer_id)

            subscription = await mark_cert_created(
                session=session,
                cer_id=subscription.cer_id,
                cert_path=cert_path,
            )

        subscription = await grant_subscription_until_2100(
            session=session,
            subscription=subscription,
        )

        try:
            await send_certificate(
                bot=message.bot,
                session=session,
                subscription=subscription,
                force=False,
            )
        except FileNotFoundError:
            await message.answer(
                "Подписка активирована до 2100 года, но файл сертификата не найден. "
                "Попробуйте позже или обратитесь в поддержку."
            )
            return

    await message.answer(
        "👑 Золотая подписка активирована до 2100 года.\n\n"
        "Теперь в профиле будет отображаться корона."
    )
