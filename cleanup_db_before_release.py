import asyncio

from sqlalchemy import text

from app.database.session import engine


TABLES_TO_CLEAN = [
    "referrals",
    "orders",
    "vpn_subscriptions",
    "users",
]


async def main():
    async with engine.begin() as conn:
        for table in TABLES_TO_CLEAN:
            await conn.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )

    print("Database cleaned successfully")


if __name__ == "__main__":
    confirm = input(
        "ВНИМАНИЕ: будут удалены users, subscriptions, orders, referrals. "
        "Напиши RELEASE чтобы продолжить: "
    )

    if confirm != "RELEASE":
        print("Cancelled")
    else:
        asyncio.run(main())
