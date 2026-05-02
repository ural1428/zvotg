import asyncio

from app.database.session import AsyncSessionLocal
from app.services.subscription_service import activate_or_extend_subscription


CER_ID = 795564969  # замени на свой telegram/chat_id


async def main():
    async with AsyncSessionLocal() as session:
        subscription = await activate_or_extend_subscription(
            session=session,
            cer_id=CER_ID,
            tariff_code="1m",
        )

        if not subscription:
            print("Subscription not found")
            return

        print("Subscription activated")
        print("expires_at:", subscription.expires_at)


asyncio.run(main())
