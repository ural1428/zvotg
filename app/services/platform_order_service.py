import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, User
from app.services.tariffs import TARIFFS


def generate_public_order_id() -> int:
    return random.randint(1000, 9999)


async def create_platform_order(
    session: AsyncSession,
    user: User,
    platform: str,
    external_id: int,
    tariff_code: str,
    action: str,
    subscription_id: int | None,
    cer_id: str | None,
    customer_email: str,
) -> Order:
    if tariff_code not in TARIFFS:
        raise ValueError("Unknown tariff")

    tariff = TARIFFS[tariff_code]

    order = Order(
        public_order_id=str(generate_public_order_id()),
        user_id=user.id,
        telegram_id=user.telegram_id,
        owner_platform=platform,
        owner_external_id=external_id,
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
