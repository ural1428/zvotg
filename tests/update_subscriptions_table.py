import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
        ALTER TABLE vpn_subscriptions
        ADD COLUMN IF NOT EXISTS tariff_code VARCHAR(20),
        ADD COLUMN IF NOT EXISTS identity_enabled BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS cert_created_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS cert_expires_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS reminded_7d BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS reminded_3d BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS reminded_1d BOOLEAN DEFAULT FALSE
        """))

    print("vpn_subscriptions table updated")


asyncio.run(main())
