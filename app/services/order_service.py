from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, User
from app.services.tariffs import TARIFFS


async def create_order(
    session: AsyncSession,
    telegram_id: int,
    tariff_code: str,
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
        status="created",
        amount=tariff.get("amount"),
    )

    session.add(order)
    await session.commit()
    await session.refresh(order)

    return order
