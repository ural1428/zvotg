import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import select

from app.config import config
from app.database.models import VPNSubscription
from app.database.session import AsyncSessionLocal

# импортируй свою готовую функцию отключения MikroTik
# пример:
# from app.services.mikrotik_service import disable_cert_id


MSK = ZoneInfo("Europe/Moscow")


def now_msk() -> datetime:
    return datetime.now(MSK)


async def send_reminders(bot: Bot):
    today = now_msk().date()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(VPNSubscription).where(
                VPNSubscription.status.in_(["paid", "sent"]),
                VPNSubscription.expires_at.is_not(None),
            )
        )

        subscriptions = result.scalars().all()

        for sub in subscriptions:
            expires_date = sub.expires_at.astimezone(MSK).date()
            days_left = (expires_date - today).days

            if days_left == 7 and not sub.reminded_7d:
                await bot.send_message(
                    sub.telegram_id,
                    "⏳ Ваша VPN-подписка закончится через 7 дней. Не забудьте продлить доступ.",
                )
                sub.reminded_7d = True

            elif days_left == 3 and not sub.reminded_3d:
                await bot.send_message(
                    sub.telegram_id,
                    "⏳ Ваша VPN-подписка закончится через 3 дня.",
                )
                sub.reminded_3d = True

            elif days_left == 1 and not sub.reminded_1d:
                await bot.send_message(
                    sub.telegram_id,
                    "⚠️ Ваша VPN-подписка закончится завтра.",
                )
                sub.reminded_1d = True

        await session.commit()


async def disable_expired_subscriptions():
    today = now_msk().date()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(VPNSubscription).where(
                VPNSubscription.identity_enabled.is_(True),
                VPNSubscription.expires_at.is_not(None),
            )
        )

        subscriptions = result.scalars().all()

        for sub in subscriptions:
            expires_date = sub.expires_at.astimezone(MSK).date()

            # отключаем только на следующий день после окончания
            if expires_date < today:
                # await disable_cert_id(sub.cer_id)

                sub.identity_enabled = False
                sub.status = "expired"

        await session.commit()


async def main(mode: str):
    bot = Bot(token=config.bot_token)

    try:
        if mode == "reminders":
            await send_reminders(bot)

        elif mode == "disable_expired":
            await disable_expired_subscriptions()

        else:
            raise ValueError("Unknown mode")

    finally:
        await bot.session.close()


if __name__ == "__main__":
    import sys

    mode = sys.argv[1]

    asyncio.run(main(mode))
