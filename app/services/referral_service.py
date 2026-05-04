from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral, User, VPNSubscription


MSK = ZoneInfo("Europe/Moscow")
REFERRAL_REWARD_DAYS = 5


def build_referral_code(telegram_id: int) -> str:
    return f"ref_{telegram_id}"


def parse_referral_code(code: str | None) -> int | None:
    if not code:
        return None

    if not code.startswith("ref_"):
        return None

    raw_id = code.replace("ref_", "", 1)

    if not raw_id.isdigit():
        return None

    return int(raw_id)


async def create_referral_if_allowed(
    session: AsyncSession,
    referrer_telegram_id: int,
    referred_telegram_id: int,
) -> Referral | None:
    if referrer_telegram_id == referred_telegram_id:
        return None

    result = await session.execute(
        select(User).where(User.telegram_id == referrer_telegram_id)
    )
    referrer = result.scalar_one_or_none()

    if not referrer:
        return None

    result = await session.execute(
        select(Referral).where(
            Referral.referred_telegram_id == referred_telegram_id
        )
    )
    existing_referral = result.scalar_one_or_none()

    if existing_referral:
        return existing_referral

    referral = Referral(
        referrer_telegram_id=referrer_telegram_id,
        referred_telegram_id=referred_telegram_id,
        status="registered",
        reward_days=REFERRAL_REWARD_DAYS,
    )

    session.add(referral)
    await session.commit()
    await session.refresh(referral)

    return referral


async def get_referral_stats(
    session: AsyncSession,
    telegram_id: int,
) -> dict:
    result = await session.execute(
        select(Referral).where(
            Referral.referrer_telegram_id == telegram_id
        )
    )

    referrals = list(result.scalars().all())

    return {
        "total": len(referrals),
        "registered": len([r for r in referrals if r.status == "registered"]),
        "rewarded": len([r for r in referrals if r.status == "rewarded"]),
        "waiting": len([r for r in referrals if r.status == "waiting_referrer_subscription"]),
    }


async def reward_referrer_for_paid_user(
    session: AsyncSession,
    referred_telegram_id: int,
) -> Referral | None:
    result = await session.execute(
        select(Referral).where(
            Referral.referred_telegram_id == referred_telegram_id
        )
    )
    referral = result.scalar_one_or_none()

    if not referral:
        return None

    if referral.status == "rewarded":
        return referral

    result = await session.execute(
        select(VPNSubscription)
        .where(VPNSubscription.telegram_id == referral.referrer_telegram_id)
        .where(VPNSubscription.status.in_(["paid", "sent"]))
        .where(VPNSubscription.expires_at.is_not(None))
        .order_by(VPNSubscription.expires_at.desc())
    )

    referrer_subscription = result.scalars().first()

    if not referrer_subscription:
        referral.status = "waiting_referrer_subscription"
        await session.commit()
        await session.refresh(referral)
        return referral

    now = datetime.now(MSK)

    if referrer_subscription.expires_at.astimezone(MSK) > now:
        referrer_subscription.expires_at = (
            referrer_subscription.expires_at + timedelta(days=referral.reward_days)
        )
    else:
        referrer_subscription.expires_at = now + timedelta(days=referral.reward_days)

    referral.status = "rewarded"
    referral.rewarded_at = now

    await session.commit()
    await session.refresh(referral)

    return referral
