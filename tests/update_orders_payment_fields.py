import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS public_order_id VARCHAR(32) UNIQUE,
            ADD COLUMN IF NOT EXISTS payment_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS payment_url VARCHAR(1000),
            ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50)
        """))

    print("orders payment fields added")


asyncio.run(main())
