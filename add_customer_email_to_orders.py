import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS customer_email VARCHAR(255)
        """))

    print("orders.customer_email added")


asyncio.run(main())
