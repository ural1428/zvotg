import argparse
import asyncio

from sqlalchemy import select

from app.config import config
from app.database.models import User
from app.database.session import AsyncSessionLocal
from app.integrations.mikrotik.manager import MikroTikManager
from app.services.subscription_service import (
    create_new_pending_subscription,
    mark_cert_created,
    activate_or_extend_subscription,
    get_user_subscriptions,
)
from app.services.tariffs import TARIFFS


async def get_or_create_manual_user(
    session,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user:
        if username:
            user.username = username
        if first_name and hasattr(user, "first_name"):
            user.first_name = first_name

        await session.commit()
        await session.refresh(user)

        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        is_active=True,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--telegram-id",
        type=int,
        required=True,
        help="Telegram ID пользователя",
    )

    parser.add_argument(
        "--tariff",
        required=True,
        help="Код тарифа из app/services/tariffs.py",
    )

    parser.add_argument(
        "--username",
        default=None,
        help="Username без @",
    )

    parser.add_argument(
        "--first-name",
        default=None,
        help="Имя пользователя",
    )

    args = parser.parse_args()

    if args.tariff not in TARIFFS:
        print("Неизвестный тариф.")
        print("Доступные тарифы:")
        for code, tariff in TARIFFS.items():
            print(f"- {code}: {tariff}")
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_manual_user(
            session=session,
            telegram_id=args.telegram_id,
            username=args.username,
            first_name=args.first_name,
        )

        existing_subscriptions = await get_user_subscriptions(
            session=session,
            telegram_id=args.telegram_id,
        )

        if len(existing_subscriptions) >= 5:
            print("У пользователя уже 5 подписок. Новую создать нельзя.")
            return

        subscription = await create_new_pending_subscription(
            session=session,
            user_id=user.id,
            telegram_id=args.telegram_id,
        )

        print(f"Создана pending-подписка:")
        print(f"id: {subscription.id}")
        print(f"cer_id: {subscription.cer_id}")

        print("Создаю сертификат на MikroTik...")

        manager = MikroTikManager(config.mikrotik)
        cert_path = await manager.certs.create_cert(subscription.cer_id)

        subscription = await mark_cert_created(
            session=session,
            cer_id=subscription.cer_id,
            cert_path=cert_path,
        )

        print(f"Сертификат создан: {subscription.cert_path}")

        subscription = await activate_or_extend_subscription(
            session=session,
            cer_id=subscription.cer_id,
            tariff_code=args.tariff,
        )

        print("Подписка активирована:")
        print(f"telegram_id: {subscription.telegram_id}")
        print(f"cer_id: {subscription.cer_id}")
        print(f"tariff_code: {subscription.tariff_code}")
        print(f"expires_at: {subscription.expires_at}")
        print(f"status: {subscription.status}")
        print(f"identity_enabled: {subscription.identity_enabled}")


if __name__ == "__main__":
    asyncio.run(main())
