import asyncio

from app.database.session import AsyncSessionLocal
from app.services.user_service import get_or_create_user
from app.services.subscription_service import create_pending_subscription
from app.database.models import User
from sqlalchemy import select


TELEGRAM_ID = 795564969  # твой telegram/chat_id
CERT_PATH = f"/storage/cert/{TELEGRAM_ID}.p12"


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == TELEGRAM_ID)
        )
        user = result.scalar_one_or_none()

        if not user:
            print("User not found. First press /start in bot.")
            return

        subscription = await create_pending_subscription(
            session=session,
            user_id=user.id,
            telegram_id=user.telegram_id,
            cer_id=user.telegram_id,
            cert_path=CERT_PATH,
        )

        print("Pending subscription created:")
        print("id:", subscription.id)
        print("cer_id:", subscription.cer_id)
        print("status:", subscription.status)


asyncio.run(main())
