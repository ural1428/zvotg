import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS reminders_sent INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS last_reminder_at TIMESTAMP WITH TIME ZONE
        """))

    print("orders reminders fields added")


asyncio.run(main())
