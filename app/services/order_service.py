from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, User
from app.services.tariffs import TARIFFS


MSK = ZoneInfo("Europe/Moscow")


async def create_order(
    session: AsyncSession,
    telegram_id: int,
    tariff_code: str,
    action: str,
    subscription_id: int | None = None,
    cer_id: str | None = None,
) -> Order:
    if tariff_code not in TARIFFS:
        raise ValueError(f"Unknown tariff_code: {tariff_code}")

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError("User not found")

    tariff = TARIFFS[tariff_code]

    order = Order(
        user_id=user.id,
        telegram_id=telegram_id,
        tariff_code=tariff_code,
        days=tariff["days"],
        amount=tariff["amount"],
        status="created",
        action=action,
        subscription_id=subscription_id,
        cer_id=cer_id,
    )

    session.add(order)
    await session.commit()
    await session.refresh(order)

    return order


async def get_order_by_id(
    session: AsyncSession,
    order_id: int,
) -> Order | None:
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def mark_order_paid(
    session: AsyncSession,
    order_id: int,
) -> Order | None:
    order = await get_order_by_id(session, order_id)

    if not order:
        return None

    order.status = "paid"
    order.paid_at = datetime.now(MSK)

    await session.commit()
    await session.refresh(order)

    return order
