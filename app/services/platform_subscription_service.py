from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, VPNSubscription


VISIBLE_SUBSCRIPTION_STATUSES = ("paid", "sent", "expired")


def build_cert_id(
    platform: str,
    external_id: int,
    index: int = 0,
) -> str:
    base = f"{platform}-{external_id}"

    if index <= 0:
        return base

    return f"{base}-{index}"


async def get_platform_user_subscriptions(
    session: AsyncSession,
    user: User,
) -> list[VPNSubscription]:
    conditions = [
        VPNSubscription.user_id == user.id,
    ]

    if user.telegram_id is not None:
        conditions.append(
            VPNSubscription.telegram_id == user.telegram_id,
        )

    if user.vk_peer_id is not None:
        conditions.append(
            and_(
                VPNSubscription.owner_platform == "vk",
                VPNSubscription.owner_external_id == user.vk_peer_id,
            )
        )

    if user.primary_platform and user.primary_external_id:
        conditions.append(
            and_(
                VPNSubscription.owner_platform == user.primary_platform,
                VPNSubscription.owner_external_id == user.primary_external_id,
            )
        )

    result = await session.execute(
        select(VPNSubscription)
        .where(or_(*conditions))
        .where(VPNSubscription.status.in_(VISIBLE_SUBSCRIPTION_STATUSES))
        .order_by(VPNSubscription.id)
    )

    return list(result.scalars().all())


async def get_active_platform_subscriptions(
    session: AsyncSession,
    user: User,
) -> list[VPNSubscription]:
    now = datetime.now(timezone.utc)

    subscriptions = await get_platform_user_subscriptions(
        session=session,
        user=user,
    )

    return [
        subscription
        for subscription in subscriptions
        if subscription.expires_at and subscription.expires_at > now
        and subscription.status in ("paid", "sent")
    ]


async def create_platform_pending_subscription(
    session: AsyncSession,
    user: User,
    platform: str,
    external_id: int,
) -> VPNSubscription:
    subscriptions = await get_platform_user_subscriptions(
        session=session,
        user=user,
    )

    if len(subscriptions) >= 5:
        raise ValueError("subscriptions_limit")

    existing_cer_ids_result = await session.execute(
        select(VPNSubscription.cer_id)
    )
    existing_cer_ids = {row[0] for row in existing_cer_ids_result.all()}

    index = 0

    while True:
        cer_id = build_cert_id(
            platform=platform,
            external_id=external_id,
            index=index,
        )

        if cer_id not in existing_cer_ids:
            break

        index += 1

    subscription = VPNSubscription(
        user_id=user.id,
        telegram_id=user.telegram_id,
        owner_platform=platform,
        owner_external_id=external_id,
        cer_id=cer_id,
        status="pending_payment",
        identity_enabled=False,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription


async def mark_platform_cert_created(
    session: AsyncSession,
    subscription: VPNSubscription,
    cert_path: str,
) -> VPNSubscription:
    subscription.cert_path = cert_path
    subscription.status = "cert_created"

    await session.commit()
    await session.refresh(subscription)

    return subscription
