import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE vpn_subscriptions
            ALTER COLUMN cer_id TYPE VARCHAR(64)
            USING cer_id::text
        """))

    print("cer_id converted to string")


asyncio.run(main())
