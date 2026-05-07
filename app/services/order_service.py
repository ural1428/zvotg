import random
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, User
from app.services.tariffs import TARIFFS


MSK = ZoneInfo("Europe/Moscow")


async def generate_public_order_id(session: AsyncSession) -> str:
    while True:
        public_order_id = str(random.randint(1000, 9999))

        result = await session.execute(
            select(Order).where(Order.public_order_id == public_order_id)
        )
        existing_order = result.scalar_one_or_none()

        if not existing_order:
            return public_order_id


async def create_order(
    session: AsyncSession,
    telegram_id: int,
    tariff_code: str,
    action: str,
    subscription_id: int | None = None,
    cer_id: str | None = None,
    customer_email: str | None = None,
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
    public_order_id = await generate_public_order_id(session)

    order = Order(
        public_order_id=public_order_id,
        user_id=user.id,
        telegram_id=telegram_id,
        tariff_code=tariff_code,
        days=tariff["days"],
        amount=tariff["amount"],
        status="created",
        action=action,
        subscription_id=subscription_id,
        cer_id=cer_id,
        customer_email=customer_email,
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
    order.payment_status = "CONFIRMED"
    order.paid_at = datetime.now(MSK)

    await session.commit()
    await session.refresh(order)

    return order


async def attach_payment_to_order(
    session: AsyncSession,
    order_id: int,
    payment_id: str,
    payment_url: str,
    payment_status: str | None = None,
) -> Order | None:
    order = await get_order_by_id(session, order_id)

    if not order:
        return None

    order.payment_id = payment_id
    order.payment_url = payment_url
    order.payment_status = payment_status or "NEW"
    order.status = "pending_payment"

    await session.commit()
    await session.refresh(order)

    return order
