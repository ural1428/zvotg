import asyncio

from sqlalchemy import delete, select

from app.database.models import User, VPNSubscription, Order, Referral
from app.database.session import AsyncSessionLocal


TELEGRAM_ID = 795564969  # замени на нужный chat_id / telegram_id


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == TELEGRAM_ID)
        )
        user = result.scalar_one_or_none()

        if not user:
            print("User not found")
            return

        print(f"Deleting user: id={user.id}, telegram_id={user.telegram_id}")

        await session.execute(
            delete(Order).where(Order.telegram_id == TELEGRAM_ID)
        )

        await session.execute(
            delete(VPNSubscription).where(VPNSubscription.telegram_id == TELEGRAM_ID)
        )

        await session.execute(
            delete(Referral).where(
                (Referral.referrer_telegram_id == TELEGRAM_ID)
                | (Referral.referred_telegram_id == TELEGRAM_ID)
            )
        )

        await session.execute(
            delete(User).where(User.telegram_id == TELEGRAM_ID)
        )

        await session.commit()

        print("User deleted")


asyncio.run(main())
