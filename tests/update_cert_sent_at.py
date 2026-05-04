import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE vpn_subscriptions
            ADD COLUMN IF NOT EXISTS cert_sent_at TIMESTAMP WITH TIME ZONE
        """))

    print("cert_sent_at added")


asyncio.run(main())
