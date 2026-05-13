import asyncio

from sqlalchemy import text

from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        # users: разрешаем Telegram ID быть пустым,
        # потому что первый вход может быть через VK.
        await conn.execute(text("""
            ALTER TABLE users
            ALTER COLUMN telegram_id DROP NOT NULL
        """))

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS vk_peer_id BIGINT UNIQUE
        """))

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS primary_platform VARCHAR(16)
        """))

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS primary_external_id BIGINT
        """))

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_merged BOOLEAN NOT NULL DEFAULT FALSE
        """))

        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS merged_into_user_id INTEGER REFERENCES users(id)
        """))

        # Заполняем текущих Telegram-пользователей как tg-аккаунты.
        await conn.execute(text("""
            UPDATE users
            SET
                primary_platform = COALESCE(primary_platform, 'tg'),
                primary_external_id = COALESCE(primary_external_id, telegram_id)
            WHERE telegram_id IS NOT NULL
        """))

        # vpn_subscriptions: добавляем владельца подписки в универсальном виде.
        await conn.execute(text("""
            ALTER TABLE vpn_subscriptions
            ALTER COLUMN telegram_id DROP NOT NULL
        """))

        await conn.execute(text("""
            ALTER TABLE vpn_subscriptions
            ADD COLUMN IF NOT EXISTS owner_platform VARCHAR(16)
        """))

        await conn.execute(text("""
            ALTER TABLE vpn_subscriptions
            ADD COLUMN IF NOT EXISTS owner_external_id BIGINT
        """))

        await conn.execute(text("""
            UPDATE vpn_subscriptions
            SET
                owner_platform = COALESCE(owner_platform, 'tg'),
                owner_external_id = COALESCE(owner_external_id, telegram_id)
            WHERE telegram_id IS NOT NULL
        """))

        # orders: добавляем владельца заказа в универсальном виде.
        await conn.execute(text("""
            ALTER TABLE orders
            ALTER COLUMN telegram_id DROP NOT NULL
        """))

        await conn.execute(text("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS owner_platform VARCHAR(16)
        """))

        await conn.execute(text("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS owner_external_id BIGINT
        """))

        await conn.execute(text("""
            UPDATE orders
            SET
                owner_platform = COALESCE(owner_platform, 'tg'),
                owner_external_id = COALESCE(owner_external_id, telegram_id)
            WHERE telegram_id IS NOT NULL
        """))

        # Таблица одноразовых кодов привязки.
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS account_link_codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(16) NOT NULL UNIQUE,

                source_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                source_platform VARCHAR(16) NOT NULL,
                source_external_id BIGINT NOT NULL,

                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                used_at TIMESTAMP WITH TIME ZONE NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_account_link_codes_code
            ON account_link_codes(code)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_account_link_codes_source_user_id
            ON account_link_codes(source_user_id)
        """))

    print("Multiplatform account fields added successfully")


if __name__ == "__main__":
    asyncio.run(main())
