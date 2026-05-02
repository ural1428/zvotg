import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("DB OK:", result.scalar())


if __name__ == "__main__":
    asyncio.run(main())
