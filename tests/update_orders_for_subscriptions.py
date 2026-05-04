import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS subscription_id INTEGER,
            ADD COLUMN IF NOT EXISTS action VARCHAR(20) NOT NULL DEFAULT 'buy',
            ADD COLUMN IF NOT EXISTS cer_id VARCHAR(64)
        """))

    print("orders updated")


asyncio.run(main())
