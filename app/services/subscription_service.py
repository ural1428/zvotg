from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import VPNSubscription
from app.services.tariffs import TARIFFS


MSK = ZoneInfo("Europe/Moscow")


async def get_subscription_by_cer_id(
    session: AsyncSession,
    cer_id: int,
) -> VPNSubscription | None:
    result = await session.execute(
        select(VPNSubscription).where(VPNSubscription.cer_id == cer_id)
    )
    return result.scalar_one_or_none()


async def get_latest_subscription(
    session: AsyncSession,
    telegram_id: int,
) -> VPNSubscription | None:
    result = await session.execute(
        select(VPNSubscription)
        .where(VPNSubscription.telegram_id == telegram_id)
        .order_by(VPNSubscription.expires_at.desc().nullslast())
    )
    return result.scalars().first()


async def create_pending_subscription(
    session: AsyncSession,
    user_id: int,
    telegram_id: int,
    cer_id: int,
    cert_path: str | None = None,
) -> VPNSubscription:
    existing_subscription = await get_subscription_by_cer_id(session, cer_id)

    if existing_subscription:
        return existing_subscription

    now = datetime.now(MSK)

    subscription = VPNSubscription(
        user_id=user_id,
        telegram_id=telegram_id,
        cer_id=cer_id,
        cert_path=cert_path,
        status="pending_payment",
        identity_enabled=False,
        cert_created_at=None,
        cert_expires_at=now + timedelta(days=372),
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription


async def mark_cert_created(
    session: AsyncSession,
    cer_id: int,
    cert_path: str,
) -> VPNSubscription | None:
    subscription = await get_subscription_by_cer_id(session, cer_id)

    if not subscription:
        return None

    now = datetime.now(MSK)

    subscription.cert_path = cert_path
    subscription.cert_created_at = now

    if subscription.cert_expires_at is None:
        subscription.cert_expires_at = now + timedelta(days=372)

    if subscription.status == "pending_payment":
        subscription.status = "cert_created"

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def activate_or_extend_subscription(
    session: AsyncSession,
    cer_id: int,
    tariff_code: str,
) -> VPNSubscription | None:
    subscription = await get_subscription_by_cer_id(session, cer_id)

    if not subscription:
        return None

    if tariff_code not in TARIFFS:
        raise ValueError(f"Unknown tariff_code: {tariff_code}")

    days = TARIFFS[tariff_code]["days"]
    now = datetime.now(MSK)

    if subscription.expires_at and subscription.expires_at.astimezone(MSK) > now:
        subscription.expires_at = subscription.expires_at + timedelta(days=days)
    else:
        subscription.expires_at = now + timedelta(days=days)

    subscription.tariff_code = tariff_code
    subscription.status = "paid"
    subscription.paid_at = now
    subscription.identity_enabled = True

    subscription.reminded_7d = False
    subscription.reminded_3d = False
    subscription.reminded_1d = False

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def mark_cert_sent(
    session: AsyncSession,
    cer_id: int,
) -> VPNSubscription | None:
    subscription = await get_subscription_by_cer_id(session, cer_id)

    if not subscription:
        return None

    subscription.cert_sent_at = datetime.now(MSK)

    if subscription.status == "paid":
        subscription.status = "sent"

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def mark_subscription_error(
    session: AsyncSession,
    cer_id: int,
) -> VPNSubscription | None:
    subscription = await get_subscription_by_cer_id(session, cer_id)

    if not subscription:
        return None

    subscription.status = "error"

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def get_active_subscription(
    session: AsyncSession,
    telegram_id: int,
) -> VPNSubscription | None:
    now = datetime.now(MSK)

    result = await session.execute(
        select(VPNSubscription)
        .where(VPNSubscription.telegram_id == telegram_id)
        .where(VPNSubscription.expires_at.is_not(None))
        .where(VPNSubscription.expires_at > now)
        .where(VPNSubscription.status.in_(["paid", "sent"]))
        .order_by(VPNSubscription.expires_at.desc())
    )

    return result.scalar_one_or_none()


def get_subscription_days_left(subscription: VPNSubscription | None) -> int:
    if not subscription or not subscription.expires_at:
        return 0

    now = datetime.now(MSK)
    expires_at = subscription.expires_at.astimezone(MSK)

    days_left = (expires_at.date() - now.date()).days

    return max(days_left, 0)


def is_subscription_active(subscription: VPNSubscription | None) -> bool:
    if not subscription or not subscription.expires_at:
        return False

    now = datetime.now(MSK)
    expires_at = subscription.expires_at.astimezone(MSK)

    return expires_at.date() >= now.date() and subscription.identity_enabled is True


async def send_certificate(
    bot: Bot,
    session: AsyncSession,
    subscription: VPNSubscription,
    force: bool = False,
) -> bool:
    """
    force=False:
        автоматически отправляем сертификат только один раз после первой оплаты.

    force=True:
        пользователь сам запросил повторную загрузку сертификата.
    """

    if not force and subscription.cert_sent_at is not None:
        return False

    if not is_subscription_active(subscription):
        raise PermissionError("Subscription is not active")

    if not subscription.cert_path:
        raise FileNotFoundError("cert_path is empty")

    cert_file = Path(subscription.cert_path)

    if not cert_file.exists():
        raise FileNotFoundError(f"Certificate file not found: {subscription.cert_path}")

    await bot.send_document(
        chat_id=subscription.telegram_id,
        document=FSInputFile(cert_file),
        caption=(
            "🔐 Ваш VPN-сертификат.\n\n"
            "Сохраните этот файл — он понадобится для подключения."
        ),
    )

    if subscription.cert_sent_at is None:
        subscription.cert_sent_at = datetime.now(MSK)

    if subscription.status == "paid":
        subscription.status = "sent"

    await session.commit()
    await session.refresh(subscription)

    return True
