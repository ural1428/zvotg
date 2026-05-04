import asyncio
from sqlalchemy import text
from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        # создаём тестовую таблицу
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            name TEXT
        )
        """))

        # вставляем пользователя
        await conn.execute(text("""
        INSERT INTO test_users (name) VALUES ('test_user')
        """))

        # читаем
        result = await conn.execute(text("SELECT * FROM test_users"))
        rows = result.fetchall()

        print("Users:", rows)


if __name__ == "__main__":
    asyncio.run(main())
