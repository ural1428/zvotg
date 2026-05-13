import asyncio

from sqlalchemy import text

from app.database.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS account_merge_requests (
                id SERIAL PRIMARY KEY,

                source_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                target_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                link_code_id INTEGER REFERENCES account_link_codes(id) ON DELETE SET NULL,

                target_platform VARCHAR(16) NOT NULL,
                target_external_id BIGINT NOT NULL,

                status VARCHAR(32) NOT NULL DEFAULT 'pending',

                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                decided_at TIMESTAMP WITH TIME ZONE NULL
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_account_merge_requests_target
            ON account_merge_requests(target_platform, target_external_id, status)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_account_merge_requests_source_user_id
            ON account_merge_requests(source_user_id)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_account_merge_requests_target_user_id
            ON account_merge_requests(target_user_id)
        """))

    print("account_merge_requests table added")


if __name__ == "__main__":
    asyncio.run(main())
